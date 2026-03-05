from __future__ import annotations

import logging
import httpx

logger = logging.getLogger(__name__)


class TwitterAPIClient:
    """Async client for OpenTwitter 6551.io REST API."""

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

    async def get_user(self, username: str) -> dict:
        return await self._post("/open/twitter_user_info", {"username": username})

    async def get_user_by_id(self, user_id: str) -> dict:
        return await self._post("/open/twitter_user_by_id", {"userId": user_id})

    async def get_user_tweets(
        self,
        username: str,
        max_results: int = 10,
        include_replies: bool = False,
        include_retweets: bool = False,
    ) -> dict:
        body = {
            "username": username,
            "maxResults": min(max_results, 100),
            "includeReplies": include_replies,
            "includeRetweets": include_retweets,
        }
        try:
            return await self._post("/open/twitter_user_tweets", body)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 400:
                raise
            try:
                profile = await self.get_user(username)
            except httpx.HTTPStatusError:
                fallback = await self.search_advanced(
                    from_user=username,
                    max_results=max_results,
                )
                fallback_tweets = fallback.get("data") or fallback.get("tweets") or []
                if fallback_tweets:
                    return {**fallback, "data": fallback_tweets[:max_results]}
                raise exc

            profile_data = profile.get("data") or profile
            canonical_username = profile_data.get("screenName") or profile_data.get("userName")
            if canonical_username and canonical_username != username:
                body["username"] = canonical_username
                return await self._post("/open/twitter_user_tweets", body)

            fallback = await self.search_advanced(
                from_user=canonical_username or username,
                max_results=max_results,
            )
            fallback_tweets = fallback.get("data") or fallback.get("tweets") or []
            if fallback_tweets:
                return {**fallback, "data": fallback_tweets[:max_results]}
            raise exc

    @staticmethod
    def _tweet_has_engagement(tweet: dict) -> bool:
        counts = [
            tweet.get("retweetCount", 0),
            tweet.get("favoriteCount", tweet.get("likeCount", 0)),
            tweet.get("replyCount", 0),
            tweet.get("quoteCount", 0),
        ]
        for value in counts:
            try:
                if int(value) > 0:
                    return True
            except (TypeError, ValueError):
                continue
        return False

    async def get_user_tweets_with_metrics(
        self,
        username: str,
        max_results: int = 10,
        include_replies: bool = False,
        include_retweets: bool = False,
    ) -> dict:
        """Fetch recent tweets and enrich zeroed metrics with indexed search data when needed."""
        primary = await self.get_user_tweets(
            username,
            max_results=max_results,
            include_replies=include_replies,
            include_retweets=include_retweets,
        )
        primary_tweets = primary.get("data") or primary.get("tweets") or []
        if not primary_tweets or any(self._tweet_has_engagement(tweet) for tweet in primary_tweets):
            return primary

        fallback = await self.search_advanced(
            from_user=username,
            max_results=min(max_results * 3, 100),
        )
        fallback_tweets = fallback.get("data") or fallback.get("tweets") or []
        if not fallback_tweets:
            return primary

        fallback_by_id = {
            str(tweet.get("id", "")): tweet
            for tweet in fallback_tweets
            if tweet.get("id")
        }

        enriched_tweets = []
        matched_metrics = False
        for tweet in primary_tweets:
            fallback_tweet = fallback_by_id.get(str(tweet.get("id", "")))
            if fallback_tweet:
                merged = {**tweet, **fallback_tweet}
                matched_metrics = matched_metrics or self._tweet_has_engagement(merged)
                enriched_tweets.append(merged)
            else:
                enriched_tweets.append(tweet)

        if matched_metrics:
            return {**primary, "data": enriched_tweets}

        if any(self._tweet_has_engagement(tweet) for tweet in fallback_tweets):
            return {**fallback, "data": fallback_tweets[:max_results]}

        return primary

    async def search(self, keywords: str, max_results: int = 10) -> dict:
        return await self._post("/open/twitter_search", {
            "keywords": keywords,
            "maxResults": min(max_results, 100),
        })

    async def search_advanced(
        self,
        keywords: str = "",
        from_user: str = "",
        min_likes: int = 0,
        min_retweets: int = 0,
        max_results: int = 10,
    ) -> dict:
        body = {
            "keywords": keywords,
            "maxResults": min(max_results, 100),
        }
        if from_user:
            body["fromUser"] = from_user
        if min_likes:
            body["minLikes"] = min_likes
        if min_retweets:
            body["minRetweets"] = min_retweets
        return await self._post("/open/twitter_search", body)

    async def get_follower_events(
        self, username: str, is_follow: bool = True, max_results: int = 10
    ) -> dict:
        return await self._post("/open/twitter_follower_events", {
            "username": username,
            "isFollow": is_follow,
            "maxResults": min(max_results, 100),
        })

    async def get_deleted_tweets(self, username: str, max_results: int = 10) -> dict:
        return await self._post("/open/twitter_deleted_tweets", {
            "username": username,
            "maxResults": min(max_results, 100),
        })

    async def get_kol_followers(self, username: str) -> dict:
        return await self._post("/open/twitter_kol_followers", {"username": username})

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
