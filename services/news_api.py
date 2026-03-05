from __future__ import annotations

import logging
import httpx

logger = logging.getLogger(__name__)


class NewsAPIClient:
    """Async client for OpenNews 6551.io REST API."""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=30.0,
            )
        return self._client

    async def _post(self, path: str, body: dict) -> dict:
        client = await self._get_client()
        for attempt in range(3):
            try:
                resp = await client.post(path, json=body)
                resp.raise_for_status()
                return resp.json()
            except httpx.ConnectError:
                if attempt == 2:
                    raise
                logger.warning(f"Connection error on {path}, retrying ({attempt + 1}/3)")
            except httpx.HTTPStatusError:
                raise

    async def _get(self, path: str) -> dict:
        client = await self._get_client()
        resp = await client.get(path)
        resp.raise_for_status()
        return resp.json()

    async def get_sources(self) -> dict:
        return await self._get("/open/news_type")

    async def get_latest(self, limit: int = 5, page: int = 1) -> dict:
        return await self._post("/open/news_search", {
            "limit": min(limit, 100),
            "page": page,
        })

    async def search(self, query: str, limit: int = 5, page: int = 1) -> dict:
        return await self._post("/open/news_search", {
            "q": query,
            "limit": min(limit, 100),
            "page": page,
        })

    async def search_by_coin(self, coin: str, limit: int = 5, page: int = 1) -> dict:
        return await self._post("/open/news_search", {
            "coins": [coin],
            "hasCoin": True,
            "limit": min(limit, 100),
            "page": page,
        })

    async def get_by_engine(self, engine_type: str, limit: int = 5, page: int = 1) -> dict:
        return await self._post("/open/news_search", {
            "engineTypes": {engine_type: True},
            "limit": min(limit, 100),
            "page": page,
        })

    async def get_high_score(self, min_score: int = 70, limit: int = 5, page: int = 1) -> dict:
        """Fetch news and filter by AI score client-side."""
        result = await self._post("/open/news_search", {
            "limit": min(limit * 3, 100),
            "page": page,
        })
        if result.get("data"):
            filtered = [
                a for a in result["data"]
                if (a.get("aiRating") or {}).get("score", 0) >= min_score
                and (a.get("aiRating") or {}).get("status") == "done"
            ]
            filtered.sort(key=lambda x: (x.get("aiRating") or {}).get("score", 0), reverse=True)
            result["data"] = filtered[:limit]
            result["total"] = len(filtered)
        return result

    async def get_by_signal(self, signal: str, limit: int = 5, page: int = 1) -> dict:
        """Fetch news and filter by trading signal client-side."""
        result = await self._post("/open/news_search", {
            "limit": min(limit * 3, 100),
            "page": page,
        })
        if result.get("data"):
            filtered = [
                a for a in result["data"]
                if (a.get("aiRating") or {}).get("signal") == signal
                and (a.get("aiRating") or {}).get("status") == "done"
            ]
            result["data"] = filtered[:limit]
            result["total"] = len(filtered)
        return result

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
