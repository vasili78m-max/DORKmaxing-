import time
import httpx
from engines.base import BaseEngine, EngineResponse, SearchResult


class SerperEngine(BaseEngine):
    name = "Serper"
    BASE_URL = "https://google.serper.dev/search"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def search(self, query: str, page: int = 1) -> EngineResponse:
        start = time.monotonic()
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "q": query,
            "num": 10,
            "page": page,
        }
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(self.BASE_URL, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            results = []
            for i, item in enumerate(data.get("organic", []), start=1):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source=self.name,
                    position=i,
                ))
            return EngineResponse(
                engine=self.name,
                results=results,
                elapsed=round(time.monotonic() - start, 2),
            )
        except httpx.HTTPStatusError as e:
            return EngineResponse(engine=self.name, error=f"HTTP {e.response.status_code}", elapsed=round(time.monotonic() - start, 2))
        except Exception as e:
            return EngineResponse(engine=self.name, error=str(e), elapsed=round(time.monotonic() - start, 2))
