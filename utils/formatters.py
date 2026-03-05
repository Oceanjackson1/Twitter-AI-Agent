import re
from datetime import datetime, timezone


def escape_md(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    special = r"_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(special)}])", r"\\\1", str(text))


def format_news_article(article: dict, lang: str = "zh") -> str:
    """Format a single news article for Telegram display."""
    text = article.get("text", "")
    link = article.get("link", "")
    engine = article.get("engineType", "")
    source = article.get("newsType", "")
    ts = article.get("ts", 0)

    ai = article.get("aiRating") or {}
    score = ai.get("score", "-")
    signal = ai.get("signal", "-")
    summary = ai.get("summary", "") if lang == "zh" else ai.get("enSummary", "")

    # Coins
    coins_list = article.get("coins") or []
    coins_str = ", ".join(c.get("symbol", "") for c in coins_list[:5]) if coins_list else ""

    # Timestamp
    time_str = ""
    if ts:
        try:
            ts_num = int(ts) if isinstance(ts, str) else ts
            dt = datetime.fromtimestamp(ts_num / 1000, tz=timezone.utc)
            time_str = dt.strftime("%Y-%m-%d %H:%M UTC")
        except (ValueError, OSError, TypeError):
            pass

    lines = []
    title = text[:120] + "..." if len(text) > 120 else text
    lines.append(f"📰 {title}")
    if summary:
        lines.append(f"   {summary[:200]}")
    if coins_str:
        lines.append(f"   💰 {coins_str}")
    meta_parts = []
    if score != "-":
        meta_parts.append(f"⭐{score}")
    if signal != "-":
        signal_emoji = {"long": "📈", "short": "📉", "neutral": "➖"}.get(signal, "")
        meta_parts.append(f"{signal_emoji}{signal}")
    if source:
        meta_parts.append(f"📂{source}")
    if meta_parts:
        lines.append(f"   {'  '.join(meta_parts)}")
    if time_str:
        lines.append(f"   🕐 {time_str}")
    if link:
        lines.append(f"   🔗 {link}")

    return "\n".join(lines)


def format_tweet(tweet: dict) -> str:
    """Format a single tweet for Telegram display."""
    text = tweet.get("text", "")
    author = tweet.get("screenName", tweet.get("userScreenName", tweet.get("author", "")))
    name = tweet.get("name", tweet.get("userName", ""))
    retweets = tweet.get("retweetCount", tweet.get("retweet_count", 0))
    likes = tweet.get("favoriteCount", tweet.get("likeCount", tweet.get("favorite_count", 0)))
    replies = tweet.get("replyCount", tweet.get("reply_count", 0))
    quotes = tweet.get("quoteCount", tweet.get("quote_count", 0))
    created = tweet.get("createdAt", tweet.get("created_at", ""))
    tweet_id = tweet.get("id", "")

    lines = []
    if author:
        if name and name.lower() != author.lower():
            lines.append(f"🐦 {name} (@{author})")
        else:
            lines.append(f"🐦 @{author}")
    lines.append(text[:500])
    lines.append(f"   💬 {replies}  🔁 {retweets}  ❤️ {likes}  📣 {quotes}")
    if created:
        lines.append(f"   🕐 {created}")
    if author and tweet_id:
        lines.append(f"   🔗 https://x.com/{author}/status/{tweet_id}")

    return "\n".join(lines)


def format_user_profile(user: dict, lang: str = "zh") -> str:
    """Format a Twitter user profile card."""
    name = user.get("name", "")
    screen = user.get("screenName", "")
    desc = user.get("description", "")
    followers = user.get("followersCount", user.get("followers", 0))
    following = user.get("friendsCount", user.get("following", 0))
    tweets = user.get("statusesCount", user.get("tweets", 0))
    verified = user.get("verified", False)

    badge = " ✅" if verified else ""
    lines = [
        f"🐦 {name} (@{screen}){badge}",
        f"{'─' * 28}",
    ]
    if desc:
        lines.append(f"📝 {desc[:200]}")
    lines.append(f"👥 {'粉丝' if lang == 'zh' else 'Followers'}: {followers:,}")
    lines.append(f"👤 {'关注' if lang == 'zh' else 'Following'}: {following:,}")
    lines.append(f"📝 {'推文' if lang == 'zh' else 'Tweets'}: {tweets:,}")

    return "\n".join(lines)


def format_tweet_alert(tweet: dict, username: str, lang: str = "zh") -> str:
    """Format a monitoring alert message."""
    text = tweet.get("text", "")
    retweets = tweet.get("retweetCount", 0)
    likes = tweet.get("favoriteCount", tweet.get("likeCount", 0))
    replies = tweet.get("replyCount", 0)
    created = tweet.get("createdAt", "")
    tweet_id = tweet.get("id", "")

    title = "🔔 新推文提醒" if lang == "zh" else "🔔 New Tweet Alert"
    lines = [
        "─────────────────────",
        title,
        f"@{username}",
        "─────────────────────",
        "",
        text[:500],
        "",
        f"💬 {replies}  🔁 {retweets}  ❤️ {likes}",
    ]
    if created:
        lines.append(f"🕐 {created}")
    if tweet_id:
        lines.append(f"🔗 https://x.com/{username}/status/{tweet_id}")
    lines.append("─────────────────────")

    return "\n".join(lines)


def split_long_message(text: str, max_len: int = 4096) -> list[str]:
    """Split a long message into chunks that fit Telegram's limit."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        # Try to split at newline
        idx = text.rfind("\n", 0, max_len)
        if idx == -1:
            idx = max_len
        chunks.append(text[:idx])
        text = text[idx:].lstrip("\n")
    return chunks
