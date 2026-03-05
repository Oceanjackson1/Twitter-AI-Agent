import logging
from telegram import BotCommand, BotCommandScopeDefault, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
from db.database import Database
from db.user_repo import UserRepo
from db.monitor_repo import MonitorRepo
from db.monitor_job_repo import MonitorJobRepo
from db.alert_repo import AlertRepo
from db.ai_repo import AIRepo
from services.news_api import NewsAPIClient
from services.twitter_api import TwitterAPIClient
from services.deepseek import DeepseekClient
from services.csv_exporter import CSVExporter
from services.heartbeat import PixelOfficeHeartbeat
from services.monitor_service import MonitorService

from bot.commands.start import start_command, help_command, lang_command
from bot.commands.news import (
    news_command,
    search_news_command,
    coin_news_command,
    hot_news_command,
    signal_command,
    sources_command,
)
from bot.commands.twitter import (
    tw_user_command,
    tw_tweets_command,
    tw_search_command,
    tw_deleted_command,
    tw_kol_command,
    tw_followers_command,
)
from bot.commands.monitor import monitor_command, unmonitor_command, monitors_command
from bot.commands.monitor import monitor_bind_command, pending_input_message_handler
from bot.commands.monitor import export_csv_command
from bot.commands.ai import ask_command, analyze_command, briefing_command
from bot.commands.account import me_command, settings_command
from bot.callbacks.inline_handlers import (
    lang_callback,
    settings_callback,
    monitor_delivery_callback,
    monitor_output_callback,
    monitor_keywords_callback,
)
from bot.callbacks.pagination import news_page_callback, noop_callback

logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Initialize services, database, and register bilingual commands."""
    heartbeat = application.bot_data.get("heartbeat")
    if heartbeat:
        await heartbeat.report_starting()

    # Database
    db = Database(config.DATABASE_PATH)
    await db.init()

    # Repositories
    user_repo = UserRepo(db)
    monitor_repo = MonitorRepo(db)
    monitor_job_repo = MonitorJobRepo(db)
    alert_repo = AlertRepo(db)
    ai_repo = AIRepo(db)

    # API Clients
    news_api = NewsAPIClient(config.OPENNEWS_API_BASE, config.OPENNEWS_TOKEN)
    twitter_api = TwitterAPIClient(config.TWITTER_API_BASE, config.TWITTER_TOKEN)
    deepseek = DeepseekClient(config.DEEPSEEK_API_KEY, config.DEEPSEEK_API_BASE)
    csv_exporter = CSVExporter()

    # Store in bot_data for access in handlers
    application.bot_data["db"] = db
    application.bot_data["user_repo"] = user_repo
    application.bot_data["monitor_repo"] = monitor_repo
    application.bot_data["monitor_job_repo"] = monitor_job_repo
    application.bot_data["alert_repo"] = alert_repo
    application.bot_data["ai_repo"] = ai_repo
    application.bot_data["news_api"] = news_api
    application.bot_data["twitter_api"] = twitter_api
    application.bot_data["deepseek"] = deepseek
    application.bot_data["csv_exporter"] = csv_exporter

    # Monitor Service
    monitor_service = MonitorService(
        twitter_api=twitter_api,
        db=db,
        user_repo=user_repo,
        monitor_repo=monitor_repo,
        monitor_job_repo=monitor_job_repo,
        alert_repo=alert_repo,
        csv_exporter=csv_exporter,
        bot=application.bot,
        poll_interval=config.MONITOR_POLL_INTERVAL,
    )
    monitor_service.start(application.job_queue)
    application.bot_data["monitor_service"] = monitor_service

    # Register bilingual command menus
    en_commands = [
        BotCommand("start", "Start bot & show welcome"),
        BotCommand("help", "Show all commands"),
        BotCommand("lang", "Switch language (CN/EN)"),
        BotCommand("news", "Latest crypto news or search"),
        BotCommand("search_news", "Search news by keyword"),
        BotCommand("coin_news", "Get news for a specific coin"),
        BotCommand("hot_news", "AI high-score news (70+)"),
        BotCommand("signal", "Filter news by signal (long/short)"),
        BotCommand("sources", "List all news sources"),
        BotCommand("tw_user", "Get Twitter user profile"),
        BotCommand("tw_tweets", "Get user's recent tweets"),
        BotCommand("tw_search", "Search tweets by keyword"),
        BotCommand("tw_deleted", "Get deleted tweets"),
        BotCommand("tw_kol", "Get KOL followers of a user"),
        BotCommand("tw_followers", "Get follow/unfollow events"),
        BotCommand("monitor", "Create a monitor job for one or more accounts"),
        BotCommand("monitor_bind", "Bind current group to pending monitor setup"),
        BotCommand("export_csv", "Export a monitor job CSV"),
        BotCommand("unmonitor", "Remove a monitor job"),
        BotCommand("monitors", "List all monitor jobs"),
        BotCommand("ask", "Ask AI about crypto markets"),
        BotCommand("analyze", "Deep AI analysis of a coin/topic"),
        BotCommand("briefing", "AI daily market briefing"),
        BotCommand("me", "View your account info"),
        BotCommand("settings", "Configure alert preferences"),
    ]

    zh_commands = [
        BotCommand("start", "启动机器人并显示欢迎信息"),
        BotCommand("help", "显示所有命令"),
        BotCommand("lang", "切换语言 (中文/英文)"),
        BotCommand("news", "获取最新加密新闻或搜索"),
        BotCommand("search_news", "按关键词搜索新闻"),
        BotCommand("coin_news", "获取特定币种新闻"),
        BotCommand("hot_news", "AI高分新闻 (70+)"),
        BotCommand("signal", "按信号筛选 (做多/做空)"),
        BotCommand("sources", "查看所有新闻来源"),
        BotCommand("tw_user", "查看推特用户信息"),
        BotCommand("tw_tweets", "获取用户最新推文"),
        BotCommand("tw_search", "按关键词搜索推文"),
        BotCommand("tw_deleted", "获取已删除推文"),
        BotCommand("tw_kol", "获取用户的KOL粉丝"),
        BotCommand("tw_followers", "获取关注/取关事件"),
        BotCommand("monitor", "创建一个支持多账号的监控任务"),
        BotCommand("monitor_bind", "将当前群组绑定到待配置监控"),
        BotCommand("export_csv", "导出某个监控任务的 CSV"),
        BotCommand("unmonitor", "移除监控任务"),
        BotCommand("monitors", "查看所有监控任务"),
        BotCommand("ask", "向AI提问加密市场"),
        BotCommand("analyze", "AI深度分析币种/话题"),
        BotCommand("briefing", "AI每日市场简报"),
        BotCommand("me", "查看个人账户信息"),
        BotCommand("settings", "配置提醒偏好"),
    ]

    await application.bot.set_my_commands(en_commands, scope=BotCommandScopeDefault())
    await application.bot.set_my_commands(
        en_commands, scope=BotCommandScopeDefault(), language_code="en"
    )
    await application.bot.set_my_commands(
        zh_commands, scope=BotCommandScopeDefault(), language_code="zh"
    )

    logger.info("Bot initialized with bilingual command menus")
    if heartbeat:
        await heartbeat.report_online()


async def post_shutdown(application: Application) -> None:
    """Clean up resources on shutdown."""
    heartbeat = application.bot_data.get("heartbeat")
    db = application.bot_data.get("db")
    if db:
        await db.close()
    news_api = application.bot_data.get("news_api")
    if news_api:
        await news_api.close()
    twitter_api = application.bot_data.get("twitter_api")
    if twitter_api:
        await twitter_api.close()
    deepseek = application.bot_data.get("deepseek")
    if deepseek:
        await deepseek.close()
    if heartbeat:
        await heartbeat.report_stopped()
        await heartbeat.close()
    logger.info("Bot shutdown complete")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global error handler."""
    logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)
    heartbeat = getattr(context.application, "bot_data", {}).get("heartbeat")
    if heartbeat:
        await heartbeat.report_exception(context.error)
    effective_message = getattr(update, "effective_message", None)
    if effective_message:
        try:
            await effective_message.reply_text(
                "Something went wrong. Please try again. / 出了点问题，请重试。"
            )
        except Exception:
            pass
    if heartbeat:
        await heartbeat.report_online()


def create_application() -> Application:
    """Create and configure the Telegram bot application."""
    app = (
        ApplicationBuilder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    app.bot_data["heartbeat"] = PixelOfficeHeartbeat.from_config(config)

    # Command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("lang", lang_command))

    # News commands
    app.add_handler(CommandHandler("news", news_command))
    app.add_handler(CommandHandler("search_news", search_news_command))
    app.add_handler(CommandHandler("seach_news", search_news_command))
    app.add_handler(CommandHandler("coin_news", coin_news_command))
    app.add_handler(CommandHandler("hot_news", hot_news_command))
    app.add_handler(CommandHandler("signal", signal_command))
    app.add_handler(CommandHandler("sources", sources_command))

    # Twitter commands
    app.add_handler(CommandHandler("tw_user", tw_user_command))
    app.add_handler(CommandHandler("tw_tweets", tw_tweets_command))
    app.add_handler(CommandHandler("tw_tweet", tw_tweets_command))
    app.add_handler(CommandHandler("tw_search", tw_search_command))
    app.add_handler(CommandHandler("tw_deleted", tw_deleted_command))
    app.add_handler(CommandHandler("tw_kol", tw_kol_command))
    app.add_handler(CommandHandler("tw_followers", tw_followers_command))

    # Monitor commands
    app.add_handler(CommandHandler("monitor", monitor_command))
    app.add_handler(CommandHandler("monitor_bind", monitor_bind_command))
    app.add_handler(CommandHandler("export_csv", export_csv_command))
    app.add_handler(CommandHandler("unmonitor", unmonitor_command))
    app.add_handler(CommandHandler("monitors", monitors_command))

    # AI commands
    app.add_handler(CommandHandler("ask", ask_command))
    app.add_handler(CommandHandler("analyze", analyze_command))
    app.add_handler(CommandHandler("briefing", briefing_command))

    # Account commands
    app.add_handler(CommandHandler("me", me_command))
    app.add_handler(CommandHandler("settings", settings_command))

    # Callback handlers
    app.add_handler(CallbackQueryHandler(lang_callback, pattern=r"^lang_"))
    app.add_handler(CallbackQueryHandler(monitor_delivery_callback, pattern=r"^monitor_delivery:"))
    app.add_handler(CallbackQueryHandler(monitor_output_callback, pattern=r"^monitor_output:"))
    app.add_handler(CallbackQueryHandler(monitor_keywords_callback, pattern=r"^monitor_keywords:"))
    app.add_handler(CallbackQueryHandler(settings_callback, pattern=r"^settings_"))
    app.add_handler(CallbackQueryHandler(news_page_callback, pattern=r"^news_page:"))
    app.add_handler(CallbackQueryHandler(noop_callback, pattern=r"^noop$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, pending_input_message_handler))

    # Error handler
    app.add_error_handler(error_handler)

    return app
