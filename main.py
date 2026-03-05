import asyncio
import logging
from dotenv import load_dotenv
from telegram import Update

import config
from bot.application import create_application
from services.heartbeat import PixelOfficeHeartbeat


async def _report_fatal_shutdown(exc: Exception) -> None:
    heartbeat = PixelOfficeHeartbeat.from_config(config)
    await heartbeat.report_exception(exc, prefix="Fatal process exception")
    await heartbeat.report_stopped()
    await heartbeat.close()


def main():
    load_dotenv()
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    # Reduce noise from httpx and apscheduler
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logger = logging.getLogger(__name__)
    logger.info(
        "Starting agent_id=%s agent_name=%s bot_username=%s app_version=%s deploy_env=%s",
        config.AGENT_ID,
        config.AGENT_NAME,
        config.BOT_USERNAME or "<unset>",
        config.APP_VERSION,
        config.DEPLOY_ENV,
    )

    app = create_application()
    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as exc:
        logging.getLogger(__name__).exception("Application crashed")
        asyncio.run(_report_fatal_shutdown(exc))
        raise


if __name__ == "__main__":
    main()
