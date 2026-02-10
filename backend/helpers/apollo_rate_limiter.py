from aiolimiter import AsyncLimiter

#Apollo allows 200 requests per minute
apollo_limiter = AsyncLimiter(max_rate=180, time_period=60)

async def rate_limited_apollo_call(func_name, *args, limiter=None, **kwargs):
    # Use the passed limiter, or fall back to the global one
    limiter_to_use = limiter if limiter is not None else apollo_limiter
    async with limiter_to_use:
        return await func_name(*args, **kwargs)