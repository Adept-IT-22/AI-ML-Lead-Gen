import pytest
import pytest_asyncio
from asyncpg import create_pool
import os
from dotenv import load_dotenv
import asyncio

# Load environment variables
load_dotenv()
DB_URL = os.getenv("MOCK_DATABASE_URL")

# Fix Windows event loop policy to avoid asyncpg loop issues
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Use pytest-asyncio marker globally
pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture(scope="function")
async def db_pool():
    """Create a database pool for tests."""
    if not DB_URL:
        pytest.skip("MOCK_DATABASE_URL not configured")

    pool = await create_pool(dsn=DB_URL, min_size=1, max_size=5)
    yield pool
    await pool.close()
