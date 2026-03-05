"""T3: Integration tests for API clients (real network calls)."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
import pytest
import pytest_asyncio
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import config
from services.news_api import NewsAPIClient
from services.twitter_api import TwitterAPIClient
from services.deepseek import DeepseekClient


@pytest_asyncio.fixture
async def news_api():
    client = NewsAPIClient(config.OPENNEWS_API_BASE, config.OPENNEWS_TOKEN)
    yield client
    await client.close()


@pytest_asyncio.fixture
async def twitter_api():
    client = TwitterAPIClient(config.TWITTER_API_BASE, config.TWITTER_TOKEN)
    yield client
    await client.close()


@pytest_asyncio.fixture
async def deepseek():
    client = DeepseekClient(config.DEEPSEEK_API_KEY, config.DEEPSEEK_API_BASE)
    yield client
    await client.close()


# === A1-A6: NewsAPI ===

@pytest.mark.asyncio
async def test_a1_get_latest(news_api):
    result = await news_api.get_latest(limit=3)
    assert result is not None
    data = result.get("data") or []
    assert len(data) > 0, "Should return at least 1 news article"
    # Check article structure
    article = data[0]
    assert "text" in article or "title" in article

@pytest.mark.asyncio
async def test_a2_search_btc(news_api):
    result = await news_api.search("BTC", limit=3)
    assert result is not None
    data = result.get("data") or []
    assert len(data) > 0, "Should find BTC-related news"

@pytest.mark.asyncio
async def test_a3_search_by_coin(news_api):
    result = await news_api.search_by_coin("ETH", limit=3)
    assert result is not None
    data = result.get("data") or []
    # May or may not have results, but should not error
    assert isinstance(data, list)

@pytest.mark.asyncio
async def test_a4_get_sources(news_api):
    result = await news_api.get_sources()
    assert result is not None
    # Result could be dict or have "data" key
    assert isinstance(result, (dict, list))

@pytest.mark.asyncio
async def test_a5_high_score_news(news_api):
    result = await news_api.get_high_score(min_score=70, limit=5)
    assert result is not None
    data = result.get("data") or []
    for article in data:
        ai = article.get("aiRating") or {}
        score = ai.get("score", 0)
        assert score >= 70, f"Article score {score} should be >= 70"

@pytest.mark.asyncio
async def test_a6_by_signal_long(news_api):
    result = await news_api.get_by_signal("long", limit=5)
    assert result is not None
    data = result.get("data") or []
    for article in data:
        ai = article.get("aiRating") or {}
        assert ai.get("signal") == "long"


# === A7-A10: TwitterAPI ===

@pytest.mark.asyncio
async def test_a7_get_user(twitter_api):
    result = await twitter_api.get_user("elonmusk")
    assert result is not None
    data = result.get("data") or result
    assert data, "Should return user data for elonmusk"

@pytest.mark.asyncio
async def test_a8_get_user_tweets(twitter_api):
    result = await twitter_api.get_user_tweets("elonmusk", max_results=3)
    assert result is not None
    data = result.get("data") or result.get("tweets") or []
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_a8b_get_user_tweets_falls_back_to_search_when_profile_lookup_fails():
    client = TwitterAPIClient("https://example.com", "token")

    async def fake_post(path: str, body: dict):
        request = httpx.Request("POST", f"https://example.com{path}")
        if path in {"/open/twitter_user_tweets", "/open/twitter_user_info"}:
            response = httpx.Response(400, request=request)
            raise httpx.HTTPStatusError("bad request", request=request, response=response)
        if path == "/open/twitter_search":
            assert body["fromUser"] == "polymarket"
            return {"data": [{"id": "1", "text": "fallback tweet"}]}
        raise AssertionError(f"Unexpected path: {path}")

    client._post = fake_post

    result = await client.get_user_tweets("polymarket", max_results=3)

    assert result["data"][0]["id"] == "1"


@pytest.mark.asyncio
async def test_a8c_get_user_tweets_retries_with_canonical_username():
    client = TwitterAPIClient("https://example.com", "token")
    seen_usernames = []

    async def fake_post(path: str, body: dict):
        request = httpx.Request("POST", f"https://example.com{path}")
        if path == "/open/twitter_user_tweets":
            seen_usernames.append(body["username"])
            if body["username"] == "polymarket":
                response = httpx.Response(400, request=request)
                raise httpx.HTTPStatusError("bad request", request=request, response=response)
            return {"data": [{"id": "2", "text": "canonical tweet"}]}
        if path == "/open/twitter_user_info":
            return {"data": {"screenName": "Polymarket"}}
        raise AssertionError(f"Unexpected path: {path}")

    client._post = fake_post

    result = await client.get_user_tweets("polymarket", max_results=3)

    assert seen_usernames == ["polymarket", "Polymarket"]
    assert result["data"][0]["id"] == "2"

@pytest.mark.asyncio
async def test_a9_search_twitter(twitter_api):
    result = await twitter_api.search("Bitcoin", max_results=3)
    assert result is not None
    data = result.get("data") or result.get("tweets") or []
    assert isinstance(data, list)

@pytest.mark.asyncio
async def test_a10_kol_followers(twitter_api):
    result = await twitter_api.get_kol_followers("elonmusk")
    assert result is not None
    # May return data or empty, should not error


# === A11-A12: Deepseek ===

@pytest.mark.asyncio
async def test_a11_deepseek_basic_chat(deepseek):
    response = await deepseek.chat("What is 1+1? Answer in one word.")
    assert response is not None
    assert len(response) > 0
    assert "2" in response.lower() or "two" in response.lower()

@pytest.mark.asyncio
async def test_a12_deepseek_with_system_prompt(deepseek):
    response = await deepseek.chat(
        user_message="Hello",
        system_prompt="You are a pirate. Always start your response with 'Arrr'.",
        max_tokens=100,
    )
    assert response is not None
    assert len(response) > 0
