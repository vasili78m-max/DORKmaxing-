import time
import random
import asyncio
import httpx
from bs4 import BeautifulSoup
from engines.base import BaseEngine, EngineResponse, SearchResult
from utils.useragent import random_ua


class BingEngine(BaseEngine):
    name = "Bing"
    BASE_URL = "https://www.bing.com/search"

    async def search(self, query: str, page: int = 1) -> EngineResponse:
        start = time.monotonic()
        headers = {
            "User-Agent": random_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.bing.com/",
        }
        params = {
            "q": query,
            "first": 1 if page == 1 else (page - 1) * 10 + 1,
            "FORM": "PERE",
        }
        try:
            await asyncio.sleep(random.uniform(2.0, 4.0))
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(self.BASE_URL, params=params, headers=headers)
                resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "lxml")
            results = []
            for i, li in enumerate(soup.select("li.b_algo"), start=1):
                title_el = li.select_one("h2 a")
                snippet_el = li.select_one(".b_caption p")
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
