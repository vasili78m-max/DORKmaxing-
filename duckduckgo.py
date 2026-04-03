import time
import random
import httpx
from bs4 import BeautifulSoup
from engines.base import BaseEngine, EngineResponse, SearchResult
from utils.useragent import random_ua


class DuckDuckGoEngine(BaseEngine):
    name = "DuckDuckGo"
    BASE_URL = "https://html.duckduckgo.com/html/"

    async def search(self, query: str, page: int = 1) -> EngineResponse:
        start = time.monotonic()
        headers = {
            "User-Agent": random_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://duckduckgo.com/",
        }
        payload = {
            "q": query,
            "b": "" if page == 1 else str((page - 1) * 10),
            "kl": "us-en",
        }
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                await asyncio.sleep(random.uniform(1.5, 3.0))
                resp = await client.post(self.BASE_URL, data=payload, headers=headers)
                resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "lxml")
            results = []
            for i, result in enumerate(soup.select(".result__body"), start=1):
                title_el = result.select_one(".result__title a")
                snippet_el = result.select_one(".result__snippet")
                if not title_el:
                    continue
                url = title_el.get("href", "")
                title = title_el.get_text(strip=True)
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                if url and title:
                    results.append(SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        source=self.name,
                        position=i,
                    ))

            return EngineResponse(
                engine=self.name,
                results=results,
                elapsed=round(time.monotonic() - start, 2),
            )
        except Exception as e:
            return EngineResponse(engine=self.name, error=str(e), elapsed=round(time.monotonic() - start, 2))


import asyncio
