import asyncio
import asyncpg
import os
from config.logging_config import setup_logging
import logging
from quart import Quart, jsonify, request, send_file, send_from_directory
from quart_cors import cors
from services.db_service import fetch_emails_sent, unsubscribe_user, get_user_by_token, add_company_note, delete_company_note, fetch_companies, fetch_people, fetch_company_details, fetch_events, mark_lead_replied, mark_lead_positive, fetch_engagement_metrics
from services.email_sending import *
from services.sendgrid_webhook import *
from services.export_to_excel import export_to_excel
from import_excel.import_excel import main as import_excel_main
from orchestration.main import main as orchestration_main 
from orchestration.outreach import main as outreach_main
from orchestration.scoring import score_and_store
import httpx
from utils.find_missing_people import find_missing_people
from healthcheck import HealthCheck

#==============================APP SETUP====================================
# Configure logging before creating quart app
setup_logging()
logger = logging.getLogger(__name__)

#The Database in use
DB_URL = os.getenv("MOCK_DATABASE_URL")

#Create quart App
app = Quart(__name__, static_folder="static", static_url_path="")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_SAMESITE="Strict",
)
app.logger.handlers = [] #Remove quart's default logging
app.logger.propagate = True #Use our configured logger
app = cors(
    app,
    allow_origin=["http://localhost:4200", "http://192.168.1.250"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    allow_credentials=True
)

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

# =============================================================================
# HEALTH CHECK
# =============================================================================
health = HealthCheck()
app.add_url_rule('health', 'health', view_func=lambda: health.run())


@app.route('/find-missing-people', methods=["GET", "POST"])
async def get_missing_people():
    logger.info("Manual trigger: Discover and enrich missing people...")
    try:
        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                await find_missing_people(pool, client)
        return jsonify({"Success": "Discover people pipeline complete"}), 200
    except Exception as e:
        logger.error(f"Failed to discover people: {str(e)}")
        return jsonify({"Error": "An unexpected error occurred", "Message": str(e)}), 500

@app.route('/run', methods=["GET", "POST"])
async def main():
    try:
        # Run the pipeline in the background
        app.add_background_task(orchestration_main)
        return jsonify({"success": "Main function done"}), 200
    except Exception as e:
        return jsonify({"Error": "An unexpected error occured", "Message": str(e) }), 500

# Feeder function for /outreach
async def outreach_task(org_ids):
        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            await outreach_main(pool, organization_ids=org_ids)

@app.route('/outreach', methods=["POST"])
async def trigger_outreach():
    logger.info("Manual trigger: Starting outreach...")
    try:
        org_ids = None
        app.add_background_task(outreach_task, org_ids=org_ids)
        return jsonify({"Success": "Outreach pipeline complete"}), 202
    except Exception as e:
        logger.error(f"Failed to run outreach: {str(e)}")
        return jsonify({"Error": str(e)}), 500

@app.route('/rescore-all', methods=["POST"])
async def rescore_all():
    logger.info("Manual trigger: Re-scoring all companies...")
    try:
        companies = await fetch_companies()
        if not companies:
            return jsonify({"Message": "No companies found to score"}), 200
        
        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            semaphore = asyncio.Semaphore(10)
            tasks = [score_and_store(pool, c.get("id"), semaphore) for c in companies]
            await asyncio.gather(*tasks)
            
        return jsonify({"Success": f"Re-scored {len(companies)} companies"}), 200
    except Exception as e:
        logger.error(f"Failed to re-score companies: {str(e)}")
        return jsonify({"Error": "An unexpected error occurred", "Message": str(e)}), 500

#Database API for fetching companies
#TO BE CHANGED!!!!
@app.route('/fetch-companies', methods=["GET"])
async def fetch_company_data():
    try:
        company_data = await fetch_companies()
    except Exception as e:
        return jsonify({"Error": "Failed to fetch companies", "Message": str(e)}), 500
    return jsonify(company_data), 200

#Database API for fetching people
@app.route('/fetch-people', methods=["GET"])
async def fetch_people_data():
    try:
        people_data = await fetch_people()
    except Exception as e:
        return jsonify({"Error": "Failed to fetch people", "Message": str(e)}), 500
    return jsonify(people_data), 200

#Database API for fetching company details
@app.route('/fetch-company-details/<id>', methods=["GET"])
async def fetch_company_details_data(id):
    try:
        company_id = int(id)
    except (ValueError, TypeError):
        return jsonify({'Error': 'Invalid company ID', 'Message': 'ID must be an integer'}), 400
    try:
        company_details = await fetch_company_details(company_id)
        if not company_details:
            return jsonify({'Error': 'No company details found', "Message": "Company details list is empty"}), 404
        return jsonify(company_details), 200
    except Exception as e:
        logger.error(f"Error fetching company details for ID {id}: {str(e)}")
        return jsonify({'Error': 'An unexpected error occurred', 'Message': str(e)}), 500

#Sendgrid webhook to receive data about emails sent
@app.route('/webhook', methods=["POST"])
async def sendgrid_events_webhook():
    logger.info("Fetching webhook event data...")

    events = await request.json
    if not events:
        return jsonify({"Error": "No events received in request body"}), 400

    try:
        # Get the running loop and schedule the update in the background
        # This allows the webhook to return 200 OK immediately and prevents loop collisions
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(update_contacted_status(events))
        else:
            # Fallback if no loop is running (unlikely during active orchestration)
            asyncio.run(update_contacted_status(events))
            
        logger.info("Webhook event data accepted for processing")
        return jsonify({"Success": "Accepted"}), 200

    except Exception as e:
        logger.error(f"Failed to accept webhook data: {str(e)}")
        return jsonify({"Error": "An unexpected error occurred", "details": str(e)}), 500

#Endpoint to fetch events
@app.route('/events', methods=["GET"])
async def get_events():
    try:
        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            events = await fetch_events(pool)
            return jsonify(events), 200
    except asyncpg.PostgresError as e:
        logger.error(f"Database error fetching events: {str(e)}")
        return jsonify([]), 500
    except Exception as e:
        logger.error(f"Failed to fetch events: {str(e)}")
        return jsonify([]), 500

@app.route('/keywords', methods=["GET"])
async def get_keywords():
    try:
        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            async with pool.acquire() as conn:
                query = "SELECT keywords FROM mock_companies"
                keyword_records = await conn.fetch(query)
                keyword_list = [dict(keywords) for keywords in keyword_records]
                return jsonify(keyword_list), 200
    except asyncpg.PostgresError as e:
        logger.error(f"Database error fetching keywords: {str(e)}")
        return jsonify({"Error": "Database error", "Message": str(e)}), 500
    except Exception as e:
        logger.error(f"Failed to fetch keywords: {str(e)}")
        return jsonify({"Error": "An unexpected error occurred", "Message": str(e)}), 500

@app.route('/export', methods=["GET"])
async def export():
    try:
        companies = await fetch_companies()
        exported_data = await export_to_excel(companies)
        if not exported_data:
            return jsonify({"Error": "No data to export"}), 400
        return send_file(exported_data, as_attachment=True)
    except Exception as e:
        return jsonify({"Error":"An unexpected error occured", "details": str(e)}), 500

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
        return jsonify({"Error": "Failed to import file", "details": str(e)}), 500

@app.route('/view-sent-emails/<company_id>', methods=["GET"])
async def get_sent_emails(company_id):
    try:
        cid = int(company_id)
    except (ValueError, TypeError):
        return jsonify({"Error": "Invalid company ID", "Message": "ID must be an integer"}), 400
    try:
        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            emails = await fetch_emails_sent(pool, cid)
        return jsonify(emails), 200
    except asyncpg.PostgresError as e:
        logger.error(f"Database error fetching sent emails for company {company_id}: {str(e)}")
        return jsonify({"Error": "Database error", "Message": str(e)}), 500
    except Exception as e:
        logger.error(f"Failed to fetch sent emails for company {company_id}: {str(e)}")
        return jsonify({"Error": "An unexpected error occurred", "Message": str(e)}), 500

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
            data = await request.json
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
        data = await request.json
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

@app.route('/engagement-metrics', methods=["GET"])
async def get_engagement_metrics():
    try:
        metrics = await fetch_engagement_metrics()
        return jsonify(metrics), 200
    except Exception as e:
        logger.error(f"Failed to fetch engagement metrics: {str(e)}")
        return jsonify({"Error": "Failed to fetch metrics", "Message": str(e)}), 500

@app.route('/mark-replied/<id>', methods=["POST"])
async def mark_replied(id):
    try:
        data = await request.json
        is_replied = data.get('replied', True)
        success = await mark_lead_replied(int(id), is_replied)
        if success:
            return jsonify({"Success": "Marked as replied"}), 200
        else:
            return jsonify({"Error": "Failed to mark as replied"}), 500
    except Exception as e:
        logger.error(f"Error marking as replied: {str(e)}")
        return jsonify({"Error": "An unexpected error occurred", "details": str(e)}), 500

@app.route('/mark-positive/<id>', methods=["POST"])
async def mark_positive(id):
    try:
        data = await request.json
        is_positive = data.get('positive', True)
        success = await mark_lead_positive(int(id), is_positive)
        if success:
            return jsonify({"Success": "Marked as positive"}), 200
        else:
            return jsonify({"Error": "Failed to mark as positive"}), 500
    except Exception as e:
        logger.error(f"Error marking as positive: {str(e)}")
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