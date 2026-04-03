import asyncio
from typing import List, Optional
from engines.base import BaseEngine, EngineResponse
from core.quota import increment_quota


async def dispatch(
    engines: List[BaseEngine],
    query: str,
    page: int = 1,
) -> List[EngineResponse]:
    tasks = [engine.search(query, page=page) for engine in engines]
    responses: List[EngineResponse] = await asyncio.gather(*tasks, return_exceptions=False)

    # count serper usage
    for r in responses:
        if r.engine == "Serper" and not r.error:
            increment_quota(1)

    return responses
