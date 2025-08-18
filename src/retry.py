from __future__ import annotations
import asyncio
import random
from typing import Callable, Type, Iterable

async def async_retry(func: Callable, exceptions: Iterable[Type[BaseException]], tries: int = 3, base_delay: float = 1.0, factor: float = 2.0, jitter: float = 0.2):
    attempt = 0
    while True:
        try:
            return await func()
        except tuple(exceptions) as e:  # type: ignore
            attempt += 1
            if attempt >= tries:
                raise
            delay = base_delay * (factor ** (attempt - 1))
            delay *= 1 + random.uniform(-jitter, jitter)
            await asyncio.sleep(delay)
