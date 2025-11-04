import os
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from services.sendgrid_webhook import update_contacted_status
import asyncpg
import asyncio
import logging
from dotenv import load_dotenv
from orchestration.ingestion import main as ingestion_main
from orchestration.normalization import main as normalization_main
from orchestration.enrichment import main as enrichment_main
from orchestration.storage import main as storage_main
from orchestration.scoring import main as scoring_main
from orchestration.outreach import main as outreach_main

load_dotenv(override=True)
DB_URL = os.getenv("DEV_DATABASE_URL")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#Create Flask App
app = Flask(__name__)
CORS(app)

@app.route('/run', methods=["GET", "POST"])
async def main():

    # ===========QUEUE CREATION ===============
    ingestion_to_normalization_queue = asyncio.Queue()
    normalization_to_enrichment_queue= asyncio.Queue()
    normalization_to_storage_queue= asyncio.Queue()
    enrichment_to_storage_queue = asyncio.Queue()

    async with asyncpg.create_pool(dsn=DB_URL, min_size=1, max_size=100) as pool:

        ingestion_module_queue = await ingestion_main(
            ingestion_to_normalization_queue
        )

        normalization_module_queues_dict = await normalization_main(
            pool,
            ingestion_to_normalization_queue=ingestion_module_queue,
            normalization_to_enrichment_queue=normalization_to_enrichment_queue,
            normalization_to_storage_queue=normalization_to_storage_queue
        )

        normalization_to_enrichment = normalization_module_queues_dict.get("normalization_to_enrichment", {})
        normalization_to_storage = normalization_module_queues_dict.get("normalization_to_storage", {})

        enrichment_module_queue = await enrichment_main(
            normalization_to_enrichment_queue=normalization_to_enrichment,
            enrichment_to_storage_queue=enrichment_to_storage_queue
        )

        await storage_main(
            pool,
            normalization_to_storage_queue=normalization_to_storage,
            enrichment_to_storage_queue=enrichment_module_queue
        )

        await scoring_main(
            pool
        )

    return jsonify({"success": "Main function done"}), 200

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

if __name__ == "__main__":
    logger.info("Application running....")
    app.run(debug=True)
    logger.info("Application Done")

