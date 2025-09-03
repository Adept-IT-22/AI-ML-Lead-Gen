from typing import Any, Union, Awaitable
from decimal import Decimal
import logging

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

#These 2 functions safely convert strings to integers and decimals
def safe_int(value: Any)->Union[int, None]:
    try: 
        return int(value)
    except (ValueError, TypeError):
        return None

def safe_decimal(value: Any)->Union[Decimal, None]:
    try:
        return Decimal(str(value))
    except (ValueError, TypeError, ArithmeticError):
        return None

#This function pairs a name with a coroutine (if all goes well) or with an exception otherwise 
async def wrap(name: str, coroutine: Awaitable[Any] )->tuple[str, Union[Any, Exception]]:
    try:
        result = await coroutine 
        logger.info(f"Coroutine {name} done")
        return name, result
    except Exception as e:
        logger.error(f"Coroutine {name} failed with the exception: {str(e)}")
        return name, e