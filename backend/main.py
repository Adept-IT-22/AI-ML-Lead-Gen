import asyncio
import asyncpg
import os
from config.logging_config import setup_logging
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
setup_logging()

#The Database in use
DB_URL = os.getenv("PROD_DATABASE_URL")

#Create Flask App
app = Flask(__name__, static_folder="static", static_url_path="")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="Strict",
)
app.logger.handlers = [] #Remove Flask's default logging
app.logger.propagate = True #Use our configured logger
CORS(app, resources={
    r"/*": {
        "origins": [
            "http://20.121.43.237",
            "http://lead-gen.adept-techno.co.ke",
            "https://lead-gen.adept-techno.co.ke"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
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
            return jsonify({"status": "error", "message": "No data received"}), 400

    except Exception as e:
        logger.error(f"Failed to get phone number: {str(e)}")
        return jsonify({"status": "error", "message": "Internal Server Error"}), 500

#Sendgrid webhook to receive data about emails sent
@app.route('/webhook', methods=["POST"])
async def sendgrid_events_webhook():
    logger.info("Fetching webhook event data...")

    events = request.json
    if not events:
        return jsonify({"Error": "No events received in request body"}), 400

    try:
        await update_contacted_status(events)
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
                query = "SELECT keywords FROM companies"
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
import ast

@app.route('/recover-logs', methods=["GET"])
async def recover_logs():
    log_data = """
2026-04-09 07:48:48,679 - root - INFO - Event is: {'email': 'asiri@lucidya.com', 'event': 'delivered', 'ip': '167.89.10.203', 'response': '250 2.0.0 OK DMARC:Quarantine 1775720874 d75a77b69052e-50db15a5c4csi63646231cf.119 - gsmtp', 'sg_event_id': 'ZGVsaXZlcmVkLTAtNTU4NzQ3NTctRXNiLW9EVFVSdFdEN3FST2VSY3BHZy0w', 'sg_message_id': 'Esb-oDTURtWD7qROeRcpGg.recvd-86b77d8cc7-8d6gn-1-69D759AA-14.0', 'smtp-id': '<Esb-oDTURtWD7qROeRcpGg@geopod-ismtpd-51>', 'timestamp': 1775720875, 'tls': 1}
2026-04-09 07:48:48,679 - root - INFO - Event is: {'email': 'asiri@lucidya.com', 'event': 'processed', 'send_at': 0, 'sg_event_id': 'cHJvY2Vzc2VkLTU1ODc0NzU3LUVzYi1vRFRVUnRXRDdxUk9lUmNwR2ctMA', 'sg_message_id': 'Esb-oDTURtWD7qROeRcpGg.recvd-86b77d8cc7-8d6gn-1-69D759AA-14.0', 'smtp-id': '<Esb-oDTURtWD7qROeRcpGg@geopod-ismtpd-51>', 'timestamp': 1775720874}
2026-04-09 07:48:50,370 - root - INFO - Event is: {'email': 'sasha@unitary.ai', 'event': 'processed', 'send_at': 0, 'sg_event_id': 'cHJvY2Vzc2VkLTU1ODc0NzU3LVNkNHJJQWdWUi1Hem1HcUhNcUFJMlEtMA', 'sg_message_id': 'Sd4rIAgVR-GzmGqHMqAI2Q.recvd-6748d45558-hfbl6-1-69D759BC-20.0', 'smtp-id': '<Sd4rIAgVR-GzmGqHMqAI2Q@geopod-ismtpd-100>', 'timestamp': 1775720892}
2026-04-09 07:48:53,197 - root - INFO - Event is: {'email': 'malte@luxurypresence.com', 'event': 'delivered', 'ip': '149.72.70.15', 'response': '250 2.0.0 OK DMARC:Quarantine 1775720916 d75a77b69052e-50d4b89ad0asi258665711cf.203 - gsmtp', 'sg_event_id': 'ZGVsaXZlcmVkLTAtNTU4NzQ3NTctTnU5VWdqNkVRTnlTR1ZVVWVzeVE0Zy0w', 'sg_message_id': 'Nu9Ugj6EQNySGVUUesyQ4g.recvd-59f49dd4cf-5hp8d-1-69D759D3-13.0', 'smtp-id': '<Nu9Ugj6EQNySGVUUesyQ4g@geopod-ismtpd-33>', 'timestamp': 1775720916, 'tls': 1}
2026-04-09 07:48:53,197 - root - INFO - Event is: {'email': 'malte@luxurypresence.com', 'event': 'processed', 'send_at': 0, 'sg_event_id': 'cHJvY2Vzc2VkLTU1ODc0NzU3LU51OVVnajZFUU55U0dWVVVlc3lRNGctMA', 'sg_message_id': 'Nu9Ugj6EQNySGVUUesyQ4g.recvd-59f49dd4cf-5hp8d-1-69D759D3-13.0', 'smtp-id': '<Nu9Ugj6EQNySGVUUesyQ4g@geopod-ismtpd-33>', 'timestamp': 1775720916}
2026-04-09 07:48:54,824 - root - INFO - Event is: {'email': 'krishna@sima.ai', 'event': 'delivered', 'ip': '149.72.70.187', 'response': '250 2.0.0 OK DMARC:Quarantine 1775720930 41be03b00d2f7-c76c662ca89si40884645a12.377 - gsmtp', 'sg_event_id': 'ZGVsaXZlcmVkLTAtNTU4NzQ3NTctQnF6MVBBNV9STVd1V3hZa1pUcmw1Zy0w', 'sg_message_id': 'Bqz1PA5_RMWuWxYkZTrl5g.recvd-6748d45558-dr5xl-1-69D759E0-7.0', 'smtp-id': '<Bqz1PA5_RMWuWxYkZTrl5g@geopod-ismtpd-114>', 'timestamp': 1775720930, 'tls': 1}
2026-04-09 07:48:54,824 - root - INFO - Event is: {'email': 'krishna@sima.ai', 'event': 'processed', 'send_at': 0, 'sg_event_id': 'cHJvY2Vzc2VkLTU1ODc0NzU3LUJxejFQQTVfUk1XdVd4WWtaVHJsNWctMA', 'sg_message_id': 'Bqz1PA5_RMWuWxYkZTrl5g.recvd-6748d45558-dr5xl-1-69D759E0-7.0', 'smtp-id': '<Bqz1PA5_RMWuWxYkZTrl5g@geopod-ismtpd-114>', 'timestamp': 1775720928}
2026-04-09 07:48:57,359 - root - INFO - Event is: {'email': 'shourya@ramain.ai', 'event': 'delivered', 'ip': '159.183.225.35', 'response': '250 2.0.0 OK DMARC:Quarantine 1775720882 6a1803df08f44-8a59381128bsi275407676d6.12 - gsmtp', 'sg_event_id': 'ZGVsaXZlcmVkLTAtNTU4NzQ3NTctanFvVVBBUENSbnFNSHplZzQwX0Zody0w', 'sg_message_id': 'jqoUPAPCRnqMHzeg40_Fhw.recvd-59f49dd4cf-nhx6w-1-69D759B0-34.0', 'smtp-id': '<jqoUPAPCRnqMHzeg40_Fhw@geopod-ismtpd-10>', 'timestamp': 1775720882, 'tls': 1}
2026-04-09 07:48:57,359 - root - INFO - Event is: {'email': 'shourya@ramain.ai', 'event': 'processed', 'send_at': 0, 'sg_event_id': 'cHJvY2Vzc2VkLTU1ODc0NzU3LWpxb1VQQVBDUm5xTUh6ZWc0MF9GaHctMA', 'sg_message_id': 'jqoUPAPCRnqMHzeg40_Fhw.recvd-59f49dd4cf-nhx6w-1-69D759B0-34.0', 'smtp-id': '<jqoUPAPCRnqMHzeg40_Fhw@geopod-ismtpd-10>', 'timestamp': 1775720880}
2026-04-09 07:48:58,229 - root - INFO - Event is: {'email': 'alex@amilabs.xyz', 'event': 'delivered', 'ip': '149.72.70.15', 'response': '250 2.0.0 OK DMARC:Quarantine 1775720887 af79cd13be357-8d2a8451cdesi2407114485a.204 - gsmtp', 'sg_event_id': 'ZGVsaXZlcmVkLTAtNTU4NzQ3NTctQVZzcWxyMndTX3EtNXFzUElZSUdVdy0w', 'sg_message_id': 'AVsqlr2wS_q-5qsPIYIGUw.recvd-59f49dd4cf-7mfwv-1-69D759B6-23.0', 'smtp-id': '<AVsqlr2wS_q-5qsPIYIGUw@geopod-ismtpd-76>', 'timestamp': 1775720887, 'tls': 1}
2026-04-09 07:48:58,229 - root - INFO - Event is: {'email': 'alex@amilabs.xyz', 'event': 'processed', 'send_at': 0, 'sg_event_id': 'cHJvY2Vzc2VkLTU1ODc0NzU3LUFWc3FscjJ3U19xLTVxc1BJWUlHVXctMA', 'sg_message_id': 'AVsqlr2wS_q-5qsPIYIGUw.recvd-59f49dd4cf-7mfwv-1-69D759B6-23.0', 'smtp-id': '<AVsqlr2wS_q-5qsPIYIGUw@geopod-ismtpd-76>', 'timestamp': 1775720886}
2026-04-09 07:49:02,581 - root - INFO - Event is: {'email': 'sasha@unitary.ai', 'event': 'delivered', 'ip': '149.72.70.187', 'response': '250 2.0.0 OK DMARC:Quarantine 1775720894 d2e1a72fcca58-82d129a68a4si35101882b3a.6 - gsmtp', 'sg_event_id': 'ZGVsaXZlcmVkLTAtNTU4NzQ3NTctU2Q0cklBZ1ZSLUd6bUdxSE1xQUkyUS0w', 'sg_message_id': 'Sd4rIAgVR-GzmGqHMqAI2Q.recvd-6748d45558-hfbl6-1-69D759BC-20.0', 'smtp-id': '<Sd4rIAgVR-GzmGqHMqAI2Q@geopod-ismtpd-100>', 'timestamp': 1775720894, 'tls': 1}
2026-04-09 07:49:04,043 - root - INFO - Event is: {'email': 'hd@datatheorem.com', 'event': 'delivered', 'ip': '159.183.225.35', 'response': '250 2.6.0 <PGkxzom6QCqkH2h1GY71LQ@geopod-ismtpd-58> [InternalId=253677948398315, Hostname=BY5PR08MB6247.namprd08.prod.outlook.com] 27762 bytes in 0.217, 124.570 KB/sec Queued mail for delivery', 'sg_event_id': 'ZGVsaXZlcmVkLTAtNTU4NzQ3NTctUEdreHpvbTZRQ3FrSDJoMUdZNzFMUS0w', 'sg_message_id': 'PGkxzom6QCqkH2h1GY71LQ.recvd-86b77d8cc7-4rflb-1-69D759C2-14.0', 'smtp-id': '<PGkxzom6QCqkH2h1GY71LQ@geopod-ismtpd-58>', 'timestamp': 1775720902, 'tls': 1}
2026-04-09 07:49:04,043 - root - INFO - Event is: {'email': 'hd@datatheorem.com', 'event': 'processed', 'send_at': 0, 'sg_event_id': 'cHJvY2Vzc2VkLTU1ODc0NzU3LVBHa3h6b202UUNxa0gyaDFHWTcxTFEtMA', 'sg_message_id': 'PGkxzom6QCqkH2h1GY71LQ.recvd-86b77d8cc7-4rflb-1-69D759C2-14.0', 'smtp-id': '<PGkxzom6QCqkH2h1GY71LQ@geopod-ismtpd-58>', 'timestamp': 1775720898}
2026-04-09 07:49:12,452 - root - INFO - Event is: {'email': 'ahmed.achchak@qevlar.com', 'event': 'delivered', 'ip': '149.72.70.15', 'response': '250 2.0.0 OK DMARC:Quarantine 1775720906 98e67ed59e1d1-35e351a81bcsi5467987a91.17 - gsmtp', 'sg_event_id': 'ZGVsaXZlcmVkLTAtNTU4NzQ3NTctdTlFa2JvbnJSaWFJU3A1Qkh2ODlEZy0w', 'sg_message_id': 'u9EkbonrRiaISp5BHv89Dg.recvd-canary-cfb76cc7f-bnqzl-1-69D759C8-11.0', 'smtp-id': '<u9EkbonrRiaISp5BHv89Dg@geopod-ismtpd-57>', 'timestamp': 1775720906, 'tls': 1}
2026-04-09 07:49:12,452 - root - INFO - Event is: {'email': 'ahmed.achchak@qevlar.com', 'event': 'processed', 'send_at': 0, 'sg_event_id': 'cHJvY2Vzc2VkLTU1ODc0NzU3LXU5RWtib25yUmlhSVNwNUJIdjg5RGctMA', 'sg_message_id': 'u9EkbonrRiaISp5BHv89Dg.recvd-canary-cfb76cc7f-bnqzl-1-69D759C8-11.0', 'smtp-id': '<u9EkbonrRiaISp5BHv89Dg@geopod-ismtpd-57>', 'timestamp': 1775720904}
2026-04-09 07:49:12,751 - root - INFO - Event is: {'email': 'copple@supabase.com', 'event': 'delivered', 'ip': '149.72.70.187', 'response': '250 2.0.0 OK DMARC:Quarantine 1775720910 d75a77b69052e-50d4b317baesi327582881cf.114 - gsmtp', 'sg_event_id': 'ZGVsaXZlcmVkLTAtNTU4NzQ3NTctdFlnRk5wVGlRODI1QjVlR2dwUEIydy0w', 'sg_message_id': 'tYgFNpTiQ825B5eGgpPB2w.recvd-86b77d8cc7-kp7hj-1-69D759CE-7.0', 'smtp-id': '<tYgFNpTiQ825B5eGgpPB2w@geopod-ismtpd-16>', 'timestamp': 1775720910, 'tls': 1}
2026-04-09 07:49:12,751 - root - INFO - Event is: {'email': 'copple@supabase.com', 'event': 'processed', 'send_at': 0, 'sg_event_id': 'cHJvY2Vzc2VkLTU1ODc0NzU3LXRZZ0ZOcFRpUTgyNUI1ZUdncFBCMnctMA', 'sg_message_id': 'tYgFNpTiQ825B5eGgpPB2w.recvd-86b77d8cc7-kp7hj-1-69D759CE-7.0', 'smtp-id': '<tYgFNpTiQ825B5eGgpPB2w@geopod-ismtpd-16>', 'timestamp': 1775720910}
2026-04-09 07:49:37,701 - root - INFO - Event is: {'email': 'philip@starcloud.com', 'event': 'delivered', 'ip': '159.183.225.35', 'response': '250 2.0.0 OK DMARC:Quarantine 1775720924 6a1803df08f44-8a598e6a782si318869006d6.658 - gsmtp', 'sg_event_id': 'ZGVsaXZlcmVkLTAtNTU4NzQ3NTctRXphaGlTTmRUTktTTVN2Ulh3dk0zdy0w', 'sg_message_id': 'EzahiSNdTNKSMSvRXwvM3w.recvd-59f49dd4cf-nhx6w-1-69D759DA-2.0', 'smtp-id': '<EzahiSNdTNKSMSvRXwvM3w@geopod-ismtpd-14>', 'timestamp': 1775720924, 'tls': 1}
"""
    events = []
    for line in log_data.strip().split("\n"):
        if "Event is: {" in line:
            dict_str = line.split("Event is: ")[1]
            try:
                event_dict = ast.literal_eval(dict_str)
                events.append(event_dict)
            except Exception as e:
                logger.error(f"Failed to parse line: {e}")

    if events:
        logger.info(f"Found {len(events)} events to process.")
        try:
            await update_contacted_status(events)
            return jsonify({"success": f"Successfully processed {len(events)} missed events"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"message": "No events parsed"}), 400

if __name__ == "__main__":
    logger.info("Application running....")
    app.run(port=5001, debug=True)
    logger.info("Application Done")