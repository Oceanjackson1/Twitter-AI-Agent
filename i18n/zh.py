STRINGS = {
    # 启动 & 帮助
    "help_text": (
        "CryptoEye Agent\n\n"
        "我是一个按需工作的加密研究与监控 Agent。\n\n"
        "📰 研究\n"
        "/news [数量|关键词] - 最新新闻或直接按关键词搜索\n"
        "/search_news <关键词> - 关键词新闻搜索\n"
        "/coin_news <币种> - 币种相关新闻\n"
        "/hot_news [最低分] - AI 高分新闻\n"
        "/signal <long|short|neutral> - 按信号筛选\n"
        "/sources - 查看新闻来源\n\n"
        "🐦 X / Twitter\n"
        "/tw_user <用户名|链接> - 用户资料\n"
        "/tw_tweets <用户名|链接> [数量] - 带互动数据的最新推文\n"
        "/tw_search <关键词> - 搜索推文\n"
        "/tw_deleted <用户名> - 已删除推文\n"
        "/tw_kol <用户名> - KOL 粉丝\n"
        "/tw_followers <用户名> - 关注事件\n\n"
        "🔔 监控 Job\n"
        "/monitor <账号1> [账号2 ...] - 创建监控任务\n"
        "/monitor_bind - 选择群组推送后，在目标群内完成绑定\n"
        "/export_csv <job_id> - 导出任务 CSV\n"
        "/monitors - 查看监控任务\n"
        "/unmonitor <job_id|用户名> - 删除监控任务\n\n"
        "🧠 AI 助手\n"
        "/ask <问题> - 带短期记忆的问答\n"
        "/analyze <币种|话题> - 结合市场上下文深度分析\n"
        "/briefing - 每日市场简报\n\n"
        "⚙️ 账户\n"
        "/start\n"
        "/lang\n"
        "/settings\n"
        "/me"
    ),

    # 语言
    "choose_language": "选择语言 / Choose your language:",
    "lang_switched": "语言已切换为中文。",

    # 新闻
    "news_title": "📰 最新加密新闻",
    "news_empty": "暂无新闻。",
    "news_search_title": "🔍 搜索结果: {keyword}",
    "news_coin_title": "📰 {coin} 相关新闻",
    "news_hot_title": "🔥 AI高分新闻 (≥{score})",
    "news_signal_title": "📊 交易信号: {signal}",
    "news_sources_title": "📂 新闻来源",
    "news_score": "评分: {score} | 信号: {signal}",
    "news_no_results": "未找到相关结果。",

    # 推特
    "tw_user_title": "🐦 推特用户: @{username}",
    "tw_tweets_title": "🐦 @{username} 的推文",
    "tw_search_title": "🔍 推文搜索: {keyword}",
    "tw_deleted_title": "🗑️ 已删除推文: @{username}",
    "tw_kol_title": "👑 KOL粉丝: @{username}",
    "tw_followers_title": "👥 关注事件: @{username}",
    "tw_no_results": "未找到相关结果。",
    "tw_user_not_found": "未找到用户 @{username}。",

    # 监控
    "monitor_added": "🔔 已开始监控 @{username}",
    "monitor_added_keywords": "🔔 已开始监控 @{username}\n关键词过滤: {keywords}",
    "monitor_removed": "🔕 已停止监控 @{username}",
    "monitor_not_found": "未在监控 @{username}",
    "monitors_title": "🔔 你的监控任务",
    "monitors_empty": "暂无监控任务。\n使用 /monitor <账号1> [账号2 ...] 添加。",
    "monitor_item": "• @{username}{keywords_info} → {destination}{status}",
    "monitor_choose_delivery": "请选择 {accounts} 的提醒投递方式：",
    "monitor_delivery_dm": "私聊",
    "monitor_delivery_group": "群组",
    "monitor_delivery_webhook": "Webhook",
    "monitor_pending_missing": "当前监控配置已过期，请重新执行 /monitor。",
    "monitor_webhook_prompt": "请发送 {accounts} 的 Webhook 地址，必须以 http:// 或 https:// 开头。",
    "monitor_invalid_webhook": "Webhook 地址无效，请发送完整的 http(s) URL。",
    "monitor_group_prompt": "请先把 Bot 拉入目标群组，然后在该群里执行 /monitor_bind，完成 {accounts} 的群组推送绑定。",
    "monitor_bind_group_only": "/monitor_bind 必须在目标群组内执行。",
    "monitor_bind_no_pending": "没有待完成的群组绑定，请先执行 /monitor。",
    "monitor_choose_output": "请选择 {accounts} 的输出方式：",
    "monitor_output_message": "消息",
    "monitor_output_csv": "CSV",
    "monitor_output_both": "消息 + CSV",
    "monitor_keywords_prompt": "已为 {accounts} 配置投递目标：{destination}\n输出方式：{output_mode}\n是否还要添加可选的关键词过滤？",
    "monitor_keywords_add": "添加关键词",
    "monitor_keywords_skip": "跳过",
    "monitor_keywords_entry": "请直接发送 {accounts} 的关键词过滤文本。\n例如：btc, etf, blackrock\n投递目标：{destination}",
    "monitor_keywords_invalid": "关键词不能为空，请发送类似：btc, etf",
    "monitor_keywords_none": "无",
    "monitor_saved": "✅ 已开始监控 @{username} → {destination}",
    "monitor_saved_keywords": "✅ 已开始监控 @{username} → {destination}\n关键词过滤: {keywords}",
    "monitor_destination_dm": "Telegram 私聊 ({target})",
    "monitor_destination_group": "Telegram 群组 ({target})",
    "monitor_destination_webhook": "Webhook ({target})",
    "monitor_job_created": (
        "✅ 已创建监控任务 #{job_id}\n"
        "账号: {accounts}\n"
        "投递目标: {destination}\n"
        "输出方式: {output_mode}\n"
        "关键词: {keywords}"
    ),
    "monitor_job_item": (
        "• 任务 #{job_id} | {count} 个账号\n"
        "  账号: {accounts}\n"
        "  投递目标: {destination}\n"
        "  输出方式: {output_mode}\n"
        "  关键词: {keywords}"
    ),
    "monitor_job_removed": "🗑️ 监控任务已删除。",
    "monitor_job_not_found": "未找到监控任务 #{job_id}。",
    "monitor_unmonitor_ambiguous": "有多个任务匹配这个用户名，请使用 /unmonitor <job_id>。",
    "monitor_csv_export_hint": "可随时使用 /export_csv {job_id} 导出 CSV",
    "monitor_csv_not_enabled": "任务 #{job_id} 未启用 CSV 输出。",
    "monitor_csv_export_caption": "任务 #{job_id} 的 CSV 导出 ({accounts})",

    # 监控告警
    "tweet_alert_title": "🔔 新推文提醒",
    "tweet_alert_from": "@{username}",

    # AI
    "ask_loading": "🤔 思考中...",
    "analyze_loading": "🔍 正在分析 {topic}... 请稍候。",
    "briefing_loading": "📊 正在生成每日简报...",
    "ai_error": "AI 分析失败，请稍后再试。",

    # 进度
    "progress_running": "⏳ 正在处理中",
    "progress_done": "✅ 处理完成",
    "progress_failed": "❌ 处理失败",
    "progress_task_line": "当前任务: {task}",
    "progress_bar_line": "进度: {bar} {percent}%",
    "progress_task_preparing": "正在准备请求",
    "progress_task_loading_page": "正在加载所选页面",
    "progress_task_fetching_news": "正在获取新闻数据",
    "progress_task_fetching_sources": "正在加载新闻来源",
    "progress_task_fetching_profile": "正在获取账号资料",
    "progress_task_fetching_tweets": "正在获取推文数据",
    "progress_task_fetching_deleted": "正在获取已删除推文记录",
    "progress_task_fetching_kol": "正在获取 KOL 粉丝",
    "progress_task_fetching_followers": "正在获取关注事件",
    "progress_task_searching_twitter": "正在搜索 X / Twitter",
    "progress_task_loading_memory": "正在加载最近对话记忆",
    "progress_task_collecting_context": "正在收集市场上下文",
    "progress_task_generating_ai": "正在生成 AI 回复",
    "progress_task_generating_briefing": "正在生成市场简报",
    "progress_task_formatting": "正在整理结果",
    "progress_task_exporting_csv": "正在生成 CSV 导出",
    "progress_task_choose_delivery": "请选择投递目标",
    "progress_task_bind_group": "请绑定目标群组",
    "progress_task_enter_webhook": "请提供 Webhook 地址",
    "progress_task_choose_output": "请选择输出方式",
    "progress_task_choose_keywords": "请选择关键词过滤方式",
    "progress_task_enter_keywords": "请提供关键词过滤",
    "progress_task_creating_job": "正在创建监控任务",
    "progress_task_result_ready": "结果已准备完成",
    "progress_task_no_results": "没有找到匹配结果",
    "progress_task_failed": "请求未能完成",

    # 账户
    "me_title": "👤 你的账户",
    "me_language": "语言: {language}",
    "me_monitors": "监控数: {count}",
    "me_created": "注册时间: {date}",
    "settings_title": "⚙️ 设置",
    "settings_max_alerts": "每日最大告警数: {count}",
    "settings_quiet": "免打扰时段: {start} - {end}",
    "settings_quiet_none": "免打扰时段: 未设置",

    # 错误
    "error_usage": "用法: {usage}",
    "error_api": "API 错误，请稍后再试。",
    "error_generic": "出了点问题，请重试。",

    # 翻页
    "page_info": "第 {current}/{total} 页",
    "page_expired": "当前结果已过期，请重新执行命令。",
}
