import os
import json
import asyncio
import asyncpg
import logging
import aiofiles
from dotenv import load_dotenv

logger = logging.getLogger()

load_dotenv(override=True)

DB_URL = os.getenv("PROD_DATABASE_URL")

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

async def update_contacted_status(events):
    logger.info(f"The DB URL is: {DB_URL}")

    """
    Updates emails_sent.status from webhook events,
    propagates status to people, then updates company status.
    """

    #Write events to file
    async with aiofiles.open("sendgrid_webhooks", "a") as file:
        await file.write(json.dumps(events, indent=2))
    
    # Build a map of emails to deduplicate and store their highest precedence status
    email_updates_map = {}
    for event in events:
        logger.info(f"Event is: {event}")
        email = event.get("email")
        sg_event = event.get("event")
        update_info = EVENT_STATUS_MAP.get(sg_event)
        
        if email and update_info:
            current_best = email_updates_map.get(email)
            if not current_best or update_info["precedence"] > current_best["precedence"]:
                email_updates_map[email] = {
                    "email": email,
                    "status": update_info["status"],
                    "precedence": update_info["precedence"]
                }

    email_updates = list(email_updates_map.values())
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
                            status contacted_status_enum,
                            precedence INTEGER
                        ) ON COMMIT DROP;
                    """)

                    # Bulk insert all email updates into the temp table
                    await conn.executemany(
                        "INSERT INTO tmp_email_status(email, status, precedence) VALUES($1, $2, $3)",
                        [(email["email"], email['status'], email['precedence']) for email in email_updates]
                    )

                    # Update emails_sent with new statuses, respecting precedence
                    # (won't downgrade e.g. 'engaged' back to 'contacted' from a later 'open' event)
                    await conn.execute("""
                        UPDATE emails_sent e
                        SET status = t.status::contacted_status_enum
                        FROM tmp_email_status t
                        JOIN people p ON LOWER(p.email) = LOWER(t.email)
                        WHERE e.recipient_id = p.id
                        AND t.precedence >= COALESCE(
                            CASE e.status::text
                                WHEN 'opted_out'  THEN 5
                                WHEN 'engaged'    THEN 4
                                WHEN 'contacted'  THEN 3
                                WHEN 'pending'    THEN 2
                                WHEN 'failed'     THEN 1
                                ELSE 0
                            END, 0
                        );
                    """
                    )

                    # Update each person's contacted_status, respecting precedence.
                    # 'open' maps to 'contacted' (precedence 3) and is handled here.
                    await conn.execute("""
                        UPDATE people p
                        SET
                            contacted_status = t.status,
                            times_contacted = times_contacted + CASE
                                WHEN t.status IN ('contacted', 'engaged') THEN 1
                                ELSE 0
                            END
                        FROM tmp_email_status t
                        WHERE LOWER(p.email) = LOWER(t.email)
                        AND t.precedence >= COALESCE(
                            CASE p.contacted_status::text
                                WHEN 'opted_out'  THEN 5
                                WHEN 'engaged'    THEN 4
                                WHEN 'contacted'  THEN 3
                                WHEN 'pending'    THEN 2
                                WHEN 'failed'     THEN 1
                                ELSE 0
                            END, 0
                        );
                    """)


                    # Get all affected organization_ids
                    org_ids = await conn.fetch("""
                        SELECT DISTINCT organization_id
                        FROM people
                        WHERE contacted_status IN ('contacted','engaged','pending','failed','opted_out')
                    """)
                    org_id_list = [record["organization_id"] for record in org_ids]

                    # Update companies based on the highest status of their people
                    if org_id_list:
                        await conn.execute("""
                            WITH company_max_status AS (
                                SELECT
                                    organization_id,
                                    MAX(
                                        CASE contacted_status
                                            WHEN 'opted_out' THEN 5
                                            WHEN 'engaged' THEN 4
                                            WHEN 'contacted' THEN 3
                                            WHEN 'pending' THEN 2
                                            WHEN 'failed' THEN 1
                                            ELSE 0
                                        END
                                    ) AS max_precedence
                                FROM people
                                WHERE organization_id = ANY($1::text[])
                                GROUP BY organization_id
                            )
                            UPDATE companies c
                            SET contacted_status = CASE cns.max_precedence
                                WHEN 5 THEN 'opted_out'::contacted_status_enum
                                WHEN 4 THEN 'engaged'::contacted_status_enum
                                WHEN 3 THEN 'contacted'::contacted_status_enum
                                WHEN 2 THEN 'pending'::contacted_status_enum
                                WHEN 1 THEN 'failed'::contacted_status_enum
                                ELSE 'uncontacted'::contacted_status_enum
                            END
                            FROM company_max_status cns
                            WHERE c.apollo_id = cns.organization_id;
                        """, org_id_list)

        logger.info(f"Updated {len(email_updates)} people and {len(org_id_list)} companies.")

    except Exception as e:
        logger.error(f"Failed to update contacted status because: {str(e)}")

# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sample_events = [
        {"email": "aalice@example.com", "event": "delivered"},
        {"email": "bbob@example.com", "event": "open"},
        {"email": "ccarol@example.com", "event": "bounce"},
        {"email": "ddave@example.com", "event": "unsubscribe"},
        {"email": "eeve@example.com", "event": "click"},
        {"email": "ffrank@example.com", "event": "processed"},
        {"email": "aaalice@example.com", "event": "click"},  # Alice gets a higher precedence event
        {"email": "bbbob@example.com", "event": "spamreport"},
        {"email": "cccarol@example.com", "event": "delivered"},  # Carol gets a better event after bounce
    ]
    asyncio.run(update_contacted_status(sample_events))