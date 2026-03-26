import asyncio
import logging
import os
from logging.handlers import RotatingFileHandler
try:
    from concurrent_log_handler import ConcurrentRotatingFileHandler
except ImportError:
    ConcurrentRotatingFileHandler = None
from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
from services.db_service import fetch_emails_sent, unsubscribe_user, get_user_by_token, add_company_note, delete_company_note
from services.email_sending import *
from services.sendgrid_webhook import *
from services.export_to_excel import export_to_excel
from import_excel.import_excel import main as import_excel_main
from orchestration.main import main as orchestration_main 

#==============================APP SETUP====================================
# Configure logging before creating Flask app
# File handler
if ConcurrentRotatingFileHandler:
    file_handler = ConcurrentRotatingFileHandler(
        "main_log.log",
        maxBytes=10000000,  # 10MB
        backupCount=5,
        encoding="utf-8"
        # use_gzip=True # Optional using gzip compression
    )
else:
    file_handler = RotatingFileHandler(
        "main_log.log",
        maxBytes=10000000,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
file_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)

#The Database in use
DB_URL = os.getenv("MOCK_DATABASE_URL")

#Create Flask App
app = Flask(__name__, static_folder="static", static_url_path="")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_SAMESITE="Strict",
)
app.logger.handlers = [] #Remove Flask's default logging
app.logger.propagate = True #Use our configured logger
CORS(app, resources={
    r"/*": {
        "origins": [
            "http://localhost:4200",
            "http://192.168.1.250"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "support_credentials": True
    }
})

#=================================APIs=======================================

# ============================================================================
# Serve React App
# ============================================================================
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, "index.html")
@app.route("/debug")
def debug():
    return {
        "static_folder": app.static_folder,
        "static_folder_exists": os.path.exists(app.static_folder),
        "static_folder_contents": os.listdir(app.static_folder) if os.path.exists(app.static_folder) else [],
        "cwd": os.getcwd(),
        "index_exists": os.path.exists(os.path.join(app.static_folder, "index.html"))
    }

@app.route('/run', methods=["GET", "POST"])
async def main():
    try:
        await orchestration_main()
        return jsonify({"success": "Main function done"}), 200
    except Exception as e:
        return jsonify({"Error": "An unexpected error occured", "Message": str(e) }), 500

#Database API for fetching companies
#TO BE CHANGED!!!!
@app.route('/fetch-companies', methods=["GET"])
async def fetch_company_data():
    company_data = await fetch_companies()
    if not company_data:
        return jsonify({"Error": "No company data found"}), 404
    return jsonify(company_data), 200

#Database API for fetching people
@app.route('/fetch-people', methods=["GET"])
async def fetch_people_data():
    people_data = await fetch_people()
    if not people_data:
        return jsonify({"Error": "No company data found"}), 404
    return jsonify(people_data), 200

#Database API for fetching company details
@app.route('/fetch-company-details/<id>', methods=["GET"])
async def fetch_company_details_data(id):
    company_details = await fetch_company_details(int(id))
    if not company_details:
        return jsonify({'Error': 'No company details found'}), 404
    return jsonify(company_details), 200

#Receive phone numbers from Apollo's People Enrichment API
#This method is dormant and not yet working.
@app.route('/apollo-phone-webhook', methods=["POST"])
async def receive_user_phone_number():
    logger.info("Receiving user phone number...")
    try:
        data = request.json
        if data:
            logger.info("Received phone number from Apollo webhook")
            logger.info(data)

            return jsonify({"status": "success", "message": "Phone number received"}), 200

        else:
            return jsonify

    except Exception as e:
        logger.error(f"Failed to get phone number: {str(e)}")
        return jsonify({"status": "error", "message": "Internal Server Error"})

#Sendgrid webhook to receive data about emails sent
@app.route('/webhook', methods=["POST"])
def sendgrid_events_webhook():
    logger.info("Fetching webhook event data...")

    events = request.json
    if not events:
        return jsonify({"Error": "No events received in request body"}), 400

    try:
        asyncio.run(update_contacted_status(events))
        logger.info("Successfully processed webhook events")
        return jsonify({"Success": "Done fetching webhook event data"}), 200

    except asyncpg.PostgresError as e:
        logger.error(f"Database error during webhook processing: {str(e)}")
        return jsonify({"error": "Database update failed", "details": str(e)}), 500

    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        return jsonify({"Error": "An unexpected error occurred", "details": str(e)}), 500

#Endpoint to fetch events
@app.route('/events', methods=["GET"])
async def get_events():
    async with asyncpg.create_pool(dsn=DB_URL) as pool:
        try:
            events = await fetch_events(pool)
            return events
        except Exception as e:
            logger.error(f"Failed to fetch events: {str(e)}")
            return []

@app.route('/keywords', methods=["GET"])
async def get_keywords():
    async with asyncpg.create_pool(dsn=DB_URL) as pool:
        async with pool.acquire() as conn:
            query = "SELECT keywords FROM companies"
            keyword_records = await conn.fetch(query)
            keyword_list = [dict(keywords) for keywords in keyword_records]
            return keyword_list

@app.route('/export', methods=["GET"])
async def export():
    companies = await fetch_companies()
    try:
        exported_data = await export_to_excel(companies)
        if not exported_data:
            return jsonify({"Error": "No data to export"}), 400
        return send_file(exported_data, as_attachment=True)
    except Exception as e:
        return jsonify({"Error":"An unexpected error occured", "details": {str(e)}}), 500

@app.route('/import-leads', methods=['POST'])
async def import_leads():
    try:
        if 'file' not in request.files:
            return jsonify({"Error": "No file in the request"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"Error": "No selected file"}), 400

        await import_excel_main(file)
        return jsonify({"Success": f"Done importing file {file.filename}"}), 200

    except Exception as e:
        logger.error(f"Failed to import excdl file: {str(e)}")
        return jsonify({"Error": "Failed to import file", "details": str(e)})

@app.route('/view-sent-emails/<company_id>', methods=["GET"])
async def get_sent_emails(company_id):
    async with asyncpg.create_pool(dsn=DB_URL) as pool:
        return await fetch_emails_sent(pool, int(company_id))

@app.route('/unsubscribe', methods=['GET', 'POST'])
async def unsubscribe():
    """
    Handle email unsubscribe requests.
    Supports GET (from email links) and POST (from API/frontend).
    """
    try:
        # 1. Get token based on request method
        if request.method == 'GET':
            token = request.args.get('token')
        else:
            data = request.json
            token = data.get('token') if data else None
        
        if not token:
            if request.method == 'GET':
                return "<h1>Error</h1><p>Unsubscribe token is missing.</p>", 400
            return jsonify({"success": False, "message": "Token is required"}), 400
        
        # 2. Perform unsubscribe
        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            success = await unsubscribe_user(pool, token)
            
            if success:
                if request.method == 'GET':
                    return """
                        <div style="font-family: sans-serif; text-align: center; margin-top: 50px;">
                            <h1>Unsubscribed</h1>
                            <p>You have been successfully unsubscribed from receiving outreach.</p>
                        </div>
                    """, 200
                return jsonify({
                    "success": True, 
                    "message": "You have been successfully unsubscribed"
                }), 200
            else:
                if request.method == 'GET':
                    return """
                        <div style="font-family: sans-serif; text-align: center; margin-top: 50px;">
                            <h1>Error</h1>
                            <p>Invalid or expired unsubscribe token.</p>
                        </div>
                    """, 404
                return jsonify({
                    "success": False, 
                    "message": "Invalid or expired unsubscribe token"
                }), 404
                
    except Exception as e:
        logger.error(f"Unsubscribe error: {str(e)}")
        if request.method == 'GET':
            return "<h1>Error</h1><p>An unexpected error occurred. Please try again later.</p>", 500
        return jsonify({
            "success": False, 
            "message": "An error occurred"
        }), 500

@app.route('/save-note/<id>', methods=["POST"])
async def save_note(id):
    try:
        data = request.json
        if not data or 'note' not in data:
            return jsonify({"Error": "No note content provided"}), 400
        
        note_text = data.get('note')
        result = await add_company_note(int(id), note_text)
        
        if result:
            return jsonify(result), 201
        else:
            return jsonify({"Error": "Failed to save note"}), 500
    except Exception as e:
        logger.error(f"Error saving note: {str(e)}")
        return jsonify({"Error": "An unexpected error occurred", "details": str(e)}), 500

@app.route('/delete-note/<note_id>', methods=["DELETE"])
async def delete_note(note_id):
    try:
        success = await delete_company_note(note_id)
        if success:
            return jsonify({"Success": "Note deleted"}), 200
        else:
            return jsonify({"Error": "Failed to delete note"}), 500
    except Exception as e:
        logger.error(f"Error deleting note: {str(e)}")
        return jsonify({"Error": "An unexpected error occurred", "details": str(e)}), 500


if __name__ == "__main__":
    logger.info("Application running....")
    app.run(port=5001, debug=True)
    logger.info("Application Done")