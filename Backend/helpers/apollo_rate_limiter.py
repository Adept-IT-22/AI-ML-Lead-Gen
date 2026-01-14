from aiolimiter import AsyncLimiter

#Apollo allows 200 requests per minute
apollo_limiter = AsyncLimiter(max_rate=180, time_period=60)

async def rate_limited_apollo_call(func_name, *args, **kwargs):
    async with apollo_limiter:
        return await func_name(*args, **kwargs)