"""T1.2: Unit tests for utils/formatters.py"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.formatters import (
    format_news_article,
    format_tweet,
    format_user_profile,
    format_tweet_alert,
    split_long_message,
    escape_md,
)


# === format_news_article ===

SAMPLE_ARTICLE = {
    "text": "Bitcoin surges past $100k as institutional buying accelerates",
    "link": "https://example.com/news/1",
    "engineType": "news",
    "newsType": "CoinDesk",
    "ts": 1709136000000,
    "aiRating": {"score": 85, "signal": "long", "status": "done", "summary": "BTC突破10万", "enSummary": "BTC breaks 100k"},
    "coins": [{"symbol": "BTC", "marketType": "spot"}],
}

def test_f1_article_basic_format():
    result = format_news_article(SAMPLE_ARTICLE, "en")
    assert "Bitcoin surges" in result
    assert "⭐85" in result
    assert "long" in result
    assert "https://example.com/news/1" in result

def test_f2_article_long_text_truncated():
    article = {**SAMPLE_ARTICLE, "text": "A" * 200}
    result = format_news_article(article, "en")
    assert "..." in result

def test_f3_article_no_ai_rating():
    article = {**SAMPLE_ARTICLE, "aiRating": None}
    result = format_news_article(article, "en")
    assert "Bitcoin surges" in result  # Should not crash

def test_f3b_article_empty_dict():
    article = {"text": "Hello", "link": "", "ts": 0}
    result = format_news_article(article, "zh")
    assert "Hello" in result

def test_f_article_chinese_summary():
    result = format_news_article(SAMPLE_ARTICLE, "zh")
    assert "BTC突破10万" in result

def test_f_article_english_summary():
    result = format_news_article(SAMPLE_ARTICLE, "en")
    assert "BTC breaks 100k" in result


# === format_tweet ===

SAMPLE_TWEET = {
    "text": "Just bought more Bitcoin! #BTC",
    "screenName": "elonmusk",
    "retweetCount": 1234,
    "favoriteCount": 5678,
    "replyCount": 890,
    "createdAt": "2026-02-28T14:30:00Z",
    "id": "123456789",
}

def test_f4_tweet_basic_format():
    result = format_tweet(SAMPLE_TWEET)
    assert "@elonmusk" in result
    assert "Just bought more Bitcoin" in result
    assert "1234" in result
    assert "5678" in result
    assert "https://x.com/elonmusk/status/123456789" in result

def test_f_tweet_minimal():
    result = format_tweet({"text": "hello"})
    assert "hello" in result

def test_f_tweet_user_screen_name_fallback():
    result = format_tweet({
        "text": "hello",
        "userScreenName": "polymarket",
        "userName": "Polymarket",
        "id": "1",
        "quoteCount": 4,
    })
    assert "@polymarket" in result
    assert "📣 4" in result


# === format_user_profile ===

SAMPLE_USER = {
    "name": "Elon Musk",
    "screenName": "elonmusk",
    "description": "Mars & Cars",
    "followersCount": 200000000,
    "friendsCount": 800,
    "statusesCount": 50000,
    "verified": True,
}

def test_f5_profile_chinese():
    result = format_user_profile(SAMPLE_USER, "zh")
    assert "粉丝" in result
    assert "Elon Musk" in result
    assert "✅" in result

def test_f6_profile_english():
    result = format_user_profile(SAMPLE_USER, "en")
    assert "Followers" in result
    assert "✅" in result

def test_f_profile_not_verified():
    user = {**SAMPLE_USER, "verified": False}
    result = format_user_profile(user, "en")
    assert "✅" not in result


# === format_tweet_alert ===

def test_f7_alert_chinese():
    result = format_tweet_alert(SAMPLE_TWEET, "elonmusk", "zh")
    assert "🔔 新推文提醒" in result
    assert "@elonmusk" in result

def test_f8_alert_english():
    result = format_tweet_alert(SAMPLE_TWEET, "elonmusk", "en")
    assert "🔔 New Tweet Alert" in result
    assert "@elonmusk" in result


# === split_long_message ===

def test_f9_short_message():
    assert split_long_message("hello") == ["hello"]

def test_f10_long_message():
    msg = ("line\n" * 2000)  # Way over 4096
    chunks = split_long_message(msg, max_len=100)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 100

def test_f_exact_limit():
    msg = "a" * 4096
    assert split_long_message(msg) == [msg]


# === escape_md ===

def test_f11_escape_special_chars():
    result = escape_md("Hello_World! [test](link) #tag")
    assert "\\_" in result
    assert "\\!" in result
    assert "\\[" in result
    assert "\\(" in result
    assert "\\#" in result

def test_f_escape_plain_text():
    result = escape_md("hello world")
    assert result == "hello world"
