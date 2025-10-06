import os
import json
import asyncio
import asyncpg
import logging
import aiofiles
from dotenv import load_dotenv

logger = logging.getLogger()

load_dotenv(override=True)

#DB_URL = os.getenv("DATABASE_URL")
DB_URL = "postgresql://lead_gen_user:lead_gen_password@localhost:2345/lead_gen_db"

async def update_contacted_status(events):
    logger.info(f"The DB URL is: {DB_URL}")

    #Write events to file
    async with aiofiles.open("sendgrid_webhooks", "a") as file:
        await file.write(json.dumps(events, indent=2))

    # We use a dictionary to map SendGrid events to a value in the contacted_status db column.
    # The 'status' is the value to be set in the database.
    # The 'precedence' is a numerical value that determines which status is "better".
    # A higher number means a higher precedence. This prevents a "bounce" from overwriting
    # a "delivered" status.
    EVENT_STATUS_MAP = {
        "processed": {"status": "pending", "precedence": 2},
        "delivered": {"status": "contacted", "precedence": 3},
        "open": {"status": "contacted", "precedence": 3},
        "click": {"status": "engaged", "precedence": 4},
        "bounce": {"status": "failed", "precedence": 1},
        "spamreport": {"status": "failed", "precedence": 1},
        "unsubscribe": {"status": "opted_out", "precedence": 5}, # A terminal status
        "dropped": {"status": "failed", "precedence": 1},
        "deferred": {"status": "pending", "precedence": 2},
    }

    """
    Processes SendGrid webhook events to update the contacted_status
    for people and their associated companies.
    """
    # Build a map of emails to their new status and precedence
    email_updates = {}
    for event in events:
        logger.info(f"Event is: {event}")
        email = event.get("email")
        sg_event = event.get("event")
        update_info = EVENT_STATUS_MAP.get(sg_event)
        
        if email and update_info:
            email_updates[email] = update_info

    if not email_updates:
        logger.info("No valid email events to process.")
        return

    try:
        async with asyncpg.create_pool(dsn=DB_URL) as pool:
            async with pool.acquire() as conn:
                # We wrap the entire operation in a transaction to ensure atomicity
                async with conn.transaction():
                    # Create a temporary table for a single, efficient update query
                    await conn.execute("""
                        CREATE TEMP TABLE tmp_email_status (
                            email TEXT PRIMARY KEY,
                            contacted_status contacted_status_enum,
                            precedence INTEGER
                        ) ON COMMIT DROP;
                    """)

                    # Bulk insert all email updates into the temp table
                    await conn.executemany(
                        "INSERT INTO tmp_email_status(email, contacted_status, precedence) VALUES($1, $2, $3)",
                        [(email, update['status'], update['precedence']) for email, update in email_updates.items()]
                    )

                    # Update people and get affected organization_ids
                    # We use a CTE with a join to the temp table to only update if
                    # the new status has a higher precedence than the current status.
                    # This prevents "bounce" from overwriting "delivered".
                    # --- ADDED contacted_status_precedence to the SET clause here ---
                    org_ids = await conn.fetch("""
                        WITH updated_people AS (
                            UPDATE people p
                            SET contacted_status = t.contacted_status::contacted_status_enum,
                                contacted_status_precedence = t.precedence
                            FROM tmp_email_status t
                            WHERE p.email = t.email
                            AND (p.contacted_status_precedence < t.precedence OR p.contacted_status_precedence IS NULL)
                            RETURNING p.organization_id
                        )
                        SELECT DISTINCT organization_id FROM updated_people;
                    """)

                    # Update companies based on the highest status of their people
                    if org_ids:
                        org_id_list = [record["organization_id"] for record in org_ids]
                        
                        await conn.execute("""
                            WITH company_new_status AS (
                                SELECT
                                    p.organization_id,
                                    MAX(p.contacted_status_precedence) AS max_precedence
                                FROM people p
                                WHERE p.organization_id = ANY($1::text[])
                                GROUP BY p.organization_id
                            )
                            UPDATE companies c
                            SET contacted_status =
                                CASE cns.max_precedence
                                    WHEN 5 THEN 'opted_out'::contacted_status_enum
                                    WHEN 4 THEN 'engaged'::contacted_status_enum
                                    WHEN 3 THEN 'contacted'::contacted_status_enum
                                    WHEN 2 THEN 'pending'::contacted_status_enum
                                    WHEN 1 THEN 'failed'::contacted_status_enum
                                    ELSE 'uncontacted'::contacted_status_enum
                                END
                            FROM company_new_status cns
                            WHERE c.apollo_id = cns.organization_id;  -- Changed c.id to c.apollo_id
                        """, org_id_list)

        logger.info(f"Updated {len(email_updates)} people and {len(org_ids)} companies.")

    except Exception as e:
        logger.error(f"Failed to update contacted status because: {str(e)}")

# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sample_events = [
        {"email": "alice@example.com", "event": "delivered"},
        {"email": "bob@example.com", "event": "open"},
        {"email": "carol@example.com", "event": "bounce"},
        {"email": "dave@example.com", "event": "unsubscribe"},
        {"email": "eve@example.com", "event": "click"},
        {"email": "frank@example.com", "event": "processed"},
        {"email": "alice@example.com", "event": "click"},  # Alice gets a higher precedence event
        {"email": "bob@example.com", "event": "spamreport"},
        {"email": "carol@example.com", "event": "delivered"},  # Carol gets a better event after bounce
    ]
    asyncio.run(update_contacted_status(sample_events))