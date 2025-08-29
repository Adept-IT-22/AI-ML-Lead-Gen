import os
import psycopg
from dotenv import load_dotenv

load_dotenv(verbose=True, override=True)

DB_URL = os.getenv("DATABASE_URL")

#Store to database
async def store_to_db(table_name: str, instruction: str)->bool:
    with psycopg.connect(conninfo=DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute()