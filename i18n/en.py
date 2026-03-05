STRINGS = {
    # Start & Help
    "help_text": (
        "CryptoEye Agent\n\n"
        "I work like an on-demand crypto research and monitoring job.\n\n"
        "📰 Research\n"
        "/news [count|keyword] - latest news or direct keyword search\n"
        "/search_news <keyword> - keyword news search\n"
        "/coin_news <symbol> - coin-specific news\n"
        "/hot_news [score] - AI high-score news\n"
        "/signal <long|short|neutral> - filter by signal\n"
        "/sources - list news sources\n\n"
        "🐦 X / Twitter\n"
        "/tw_user <username|url> - user profile\n"
        "/tw_tweets <username|url> [count] - recent tweets with engagement\n"
        "/tw_search <keyword> - tweet search\n"
        "/tw_deleted <username> - deleted tweets\n"
        "/tw_kol <username> - KOL followers\n"
        "/tw_followers <username> - follow events\n\n"
        "🔔 Monitoring Jobs\n"
        "/monitor <account1> [account2 ...] - build a monitor job\n"
        "/monitor_bind - finish binding after choosing group delivery\n"
        "/export_csv <job_id> - export a job CSV\n"
        "/monitors - list your monitor jobs\n"
        "/unmonitor <job_id|username> - remove a monitor job\n\n"
        "🧠 AI Copilot\n"
        "/ask <question> - chat with short-term memory\n"
        "/analyze <coin|topic> - deeper analysis with market context\n"
        "/briefing - daily market briefing\n\n"
        "⚙️ Account\n"
        "/start\n"
        "/lang\n"
        "/settings\n"
        "/me"
    ),

    # Language
    "choose_language": "Choose your language / 选择语言:",
    "lang_switched": "Language switched to English.",

    # News
    "news_title": "📰 Latest Crypto News",
    "news_empty": "No news found.",
    "news_search_title": "🔍 Search Results: {keyword}",
    "news_coin_title": "📰 News for {coin}",
    "news_hot_title": "🔥 High-Score News (≥{score})",
    "news_signal_title": "📊 Signal: {signal}",
    "news_sources_title": "📂 News Sources",
    "news_score": "Score: {score} | Signal: {signal}",
    "news_no_results": "No results found.",

    # Twitter
    "tw_user_title": "🐦 Twitter User: @{username}",
    "tw_tweets_title": "🐦 Tweets from @{username}",
    "tw_search_title": "🔍 Tweet Search: {keyword}",
    "tw_deleted_title": "🗑️ Deleted Tweets: @{username}",
    "tw_kol_title": "👑 KOL Followers: @{username}",
    "tw_followers_title": "👥 Follow Events: @{username}",
    "tw_no_results": "No results found.",
    "tw_user_not_found": "User @{username} not found.",

    # Monitor
    "monitor_added": "🔔 Now monitoring @{username}",
    "monitor_added_keywords": "🔔 Now monitoring @{username}\nKeywords: {keywords}",
    "monitor_removed": "🔕 Stopped monitoring @{username}",
    "monitor_not_found": "Not monitoring @{username}",
    "monitors_title": "🔔 Your Monitor Jobs",
    "monitors_empty": "You have no monitor jobs.\nUse /monitor <account1> [account2 ...] to add one.",
    "monitor_item": "• @{username}{keywords_info} → {destination}{status}",
    "monitor_choose_delivery": "Choose where updates for {accounts} should be delivered:",
    "monitor_delivery_dm": "DM",
    "monitor_delivery_group": "Group",
    "monitor_delivery_webhook": "Webhook",
    "monitor_pending_missing": "This monitor setup expired. Run /monitor again.",
    "monitor_webhook_prompt": "Send the webhook URL for {accounts}. It must start with http:// or https://",
    "monitor_invalid_webhook": "Invalid webhook URL. Send a full http(s) URL.",
    "monitor_group_prompt": (
        "Add this bot to the target group, then run /monitor_bind in that group "
        "to finish linking alerts for {accounts}."
    ),
    "monitor_bind_group_only": "/monitor_bind must be run inside the target group.",
    "monitor_bind_no_pending": "No pending group setup found. Start with /monitor first.",
    "monitor_choose_output": "Choose the output mode for {accounts}:",
    "monitor_output_message": "Messages",
    "monitor_output_csv": "CSV",
    "monitor_output_both": "Messages + CSV",
    "monitor_keywords_prompt": (
        "Delivery for {accounts} is ready: {destination}\n"
        "Output mode: {output_mode}\n"
        "Do you want to add an optional keyword filter?"
    ),
    "monitor_keywords_add": "Add keywords",
    "monitor_keywords_skip": "Skip",
    "monitor_keywords_entry": (
        "Send the keyword filter for {accounts} as plain text.\n"
        "Example: btc, etf, blackrock\n"
        "Destination: {destination}"
    ),
    "monitor_keywords_invalid": "Keyword filter cannot be empty. Send text like: btc, etf",
    "monitor_keywords_none": "None",
    "monitor_saved": "✅ Monitoring @{username} → {destination}",
    "monitor_saved_keywords": "✅ Monitoring @{username} → {destination}\nKeywords: {keywords}",
    "monitor_destination_dm": "Telegram DM ({target})",
    "monitor_destination_group": "Telegram Group ({target})",
    "monitor_destination_webhook": "Webhook ({target})",
    "monitor_job_created": (
        "✅ Monitor Job #{job_id} created\n"
        "Accounts: {accounts}\n"
        "Destination: {destination}\n"
        "Output: {output_mode}\n"
        "Keywords: {keywords}"
    ),
    "monitor_job_item": (
        "• Job #{job_id} | {count} accounts\n"
        "  Accounts: {accounts}\n"
        "  Destination: {destination}\n"
        "  Output: {output_mode}\n"
        "  Keywords: {keywords}"
    ),
    "monitor_job_removed": "🗑️ Monitor job removed.",
    "monitor_job_not_found": "Monitor job #{job_id} was not found.",
    "monitor_unmonitor_ambiguous": "More than one job matches that username. Use /unmonitor <job_id>.",
    "monitor_csv_export_hint": "Export anytime with /export_csv {job_id}",
    "monitor_csv_not_enabled": "CSV output is not enabled for job #{job_id}.",
    "monitor_csv_export_caption": "CSV export for job #{job_id} ({accounts})",

    # Monitor Alerts
    "tweet_alert_title": "🔔 New Tweet Alert",
    "tweet_alert_from": "@{username}",

    # AI
    "ask_loading": "🤔 Thinking...",
    "analyze_loading": "🔍 Analyzing {topic}... This may take a moment.",
    "briefing_loading": "📊 Generating daily briefing...",
    "ai_error": "AI analysis failed. Please try again later.",

    # Progress
    "progress_running": "⏳ Processing request",
    "progress_done": "✅ Completed",
    "progress_failed": "❌ Failed",
    "progress_task_line": "Current task: {task}",
    "progress_bar_line": "Progress: {bar} {percent}%",
    "progress_task_preparing": "Preparing your request",
    "progress_task_loading_page": "Loading the selected page",
    "progress_task_fetching_news": "Fetching news data",
    "progress_task_fetching_sources": "Loading news sources",
    "progress_task_fetching_profile": "Fetching account profile",
    "progress_task_fetching_tweets": "Fetching tweet data",
    "progress_task_fetching_deleted": "Fetching deleted tweet history",
    "progress_task_fetching_kol": "Fetching KOL followers",
    "progress_task_fetching_followers": "Fetching follow events",
    "progress_task_searching_twitter": "Searching X / Twitter",
    "progress_task_loading_memory": "Loading recent conversation memory",
    "progress_task_collecting_context": "Collecting market context",
    "progress_task_generating_ai": "Generating AI response",
    "progress_task_generating_briefing": "Generating market briefing",
    "progress_task_formatting": "Formatting results",
    "progress_task_exporting_csv": "Building CSV export",
    "progress_task_choose_delivery": "Choose the delivery target",
    "progress_task_bind_group": "Bind the target group",
    "progress_task_enter_webhook": "Provide a webhook URL",
    "progress_task_choose_output": "Choose the output mode",
    "progress_task_choose_keywords": "Choose keyword filtering",
    "progress_task_enter_keywords": "Provide keyword filters",
    "progress_task_creating_job": "Creating the monitor job",
    "progress_task_result_ready": "Result is ready",
    "progress_task_no_results": "No matching results found",
    "progress_task_failed": "The request could not be completed",

    # Account
    "me_title": "👤 Your Account",
    "me_language": "Language: {language}",
    "me_monitors": "Monitors: {count}",
    "me_created": "Since: {date}",
    "settings_title": "⚙️ Settings",
    "settings_max_alerts": "Max daily alerts: {count}",
    "settings_quiet": "Quiet hours: {start} - {end}",
    "settings_quiet_none": "Quiet hours: Not set",

    # Errors
    "error_usage": "Usage: {usage}",
    "error_api": "API error. Please try again later.",
    "error_generic": "Something went wrong. Please try again.",

    # Pagination
    "page_info": "Page {current}/{total}",
    "page_expired": "This result expired. Please run the command again.",
}
