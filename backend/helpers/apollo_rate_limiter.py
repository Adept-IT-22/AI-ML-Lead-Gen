import asyncio
import logging
import time
from collections import deque
from typing import Callable, Any
from tenacity import retry, wait_exponential, stop_after_attempt, RetryCallState, retry_if_exception

# --- Configuration ---
MAX_CALLS = 200         # Max requests per minute
WINDOW_SECONDS = 60     # 1 minute window
MIN_CALL_GAP_SECONDS = 0.4  # Minimum gap between consecutive calls
lock = asyncio.Lock()   # Protect deque for concurrency
call_timestamps: deque[float] = deque()
last_call_time: float = 0.0
logger = logging.getLogger(__name__)

# --- Rate limit error detection ---
def is_rate_limit_error(exception: BaseException) -> bool:
    """Check if the exception is an HTTP 429 Too Many Requests error."""
    from httpx import HTTPStatusError
    if isinstance(exception, HTTPStatusError):
        logger.error("429 error encountered")
        return exception.response.status_code == 429
    msg = str(exception).lower()
    return "429" in msg or "too many requests" in msg

# --- Retry logging ---
def log_before_retry(retry_state: RetryCallState):
    logger.warning(
        f"Apollo API call rate limited. Retrying... attempt #{retry_state.attempt_number}"
    )

def log_failure(retry_state: RetryCallState):
    logger.error(
        f"Apollo API failed after {retry_state.attempt_number} retries. "
        f"Error: {retry_state.outcome.exception() if retry_state.outcome else 'Unknown'}"
    )
    return None

# --- Retry wrapper ---
@retry(
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(5),
    retry=retry_if_exception(is_rate_limit_error),
    before=log_before_retry,
    retry_error_callback=log_failure,
    reraise=True
)
async def _execute_with_retry(func: Callable, *args, **kwargs) -> Any:
    """Executes a function with retry logic specifically for rate limits."""
    return await func(*args, **kwargs)

# --- Deque-based rate-limited call ---
async def rate_limited_apollo_call(func: Callable, *args, **kwargs) -> Any:
    """
    Ensures no more than MAX_CALLS per WINDOW_SECONDS.
    Combines deque-based rate limiting with retry logic for 429 errors.
    """
    async with lock:
        now = asyncio.get_running_loop().time()

        # Enforce minimum gap between consecutive calls
        global last_call_time
        elapsed_since_last = now - last_call_time
        if elapsed_since_last < MIN_CALL_GAP_SECONDS:
            await asyncio.sleep(MIN_CALL_GAP_SECONDS - elapsed_since_last)
            now = asyncio.get_running_loop().time()

        # Remove timestamps outside the window
        while call_timestamps and now - call_timestamps[0] > WINDOW_SECONDS:
            call_timestamps.popleft()

        if len(call_timestamps) >= MAX_CALLS:
            # Wait until oldest timestamp is outside the window
            wait_time = WINDOW_SECONDS - (now - call_timestamps[0])
            logger.info(f"Rate limit reached. Sleeping for {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
            now = asyncio.get_running_loop().time()
            while call_timestamps and now - call_timestamps[0] > WINDOW_SECONDS:
                call_timestamps.popleft()

        # Record this call
        call_timestamps.append(now)
        last_call_time = now

    # Execute the function with retry logic for 429s
    return await _execute_with_retry(func, *args, **kwargs)