import os
from functools import lru_cache


@lru_cache(maxsize=1)
def get_start_balance() -> float:
    """Return the initial balance for newly created users."""
    value = os.getenv("START_BALANCE")
    if value is not None:
        try:
            return float(value)
        except (ValueError, TypeError):
            pass
    return 1.0
