import os
from dotenv import load_dotenv

load_dotenv()

AGENT_ID = os.getenv("AGENT_ID", "polymarket-ai-agent")
AGENT_NAME = os.getenv("AGENT_NAME", "CryptoEye Agent")
BOT_USERNAME = os.getenv("BOT_USERNAME", "")
APP_VERSION = os.getenv("APP_VERSION", "local-dev")
DEPLOY_ENV = os.getenv("DEPLOY_ENV", "development")
COMPOSE_PROJECT_NAME = os.getenv("COMPOSE_PROJECT_NAME", "polymarket-ai-agent")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OPENNEWS_TOKEN = os.getenv("OPENNEWS_TOKEN", "")
TWITTER_TOKEN = os.getenv("TWITTER_TOKEN", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

OPENNEWS_API_BASE = os.getenv("OPENNEWS_API_BASE", "https://ai.6551.io")
TWITTER_API_BASE = os.getenv("TWITTER_API_BASE", "https://ai.6551.io")
DEEPSEEK_API_BASE = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")

DATABASE_PATH = os.getenv("DATABASE_PATH", "data/bot.db")
MONITOR_POLL_INTERVAL = int(os.getenv("MONITOR_POLL_INTERVAL", "60"))

PIXEL_OFFICE_HEARTBEAT_ENABLED = os.getenv("PIXEL_OFFICE_HEARTBEAT_ENABLED", "1").lower() not in {
    "0",
    "false",
    "off",
    "no",
}
PIXEL_OFFICE_ENDPOINT = os.getenv(
    "PIXEL_OFFICE_ENDPOINT",
    "https://ewsrmznakzzkkcwftgjd.supabase.co/rest/v1/agents",
)
PIXEL_OFFICE_API_KEY = os.getenv(
    "PIXEL_OFFICE_API_KEY",
    "sb_publishable_pbt93uIf5oX9xN1taOVJUQ_mCQve3M4",
)
PIXEL_OFFICE_AGENT_ID = os.getenv("PIXEL_OFFICE_AGENT_ID", "cryptoeye-agent-main")
PIXEL_OFFICE_AGENT_NAME = os.getenv("PIXEL_OFFICE_AGENT_NAME", "CryptoEye Agent")
PIXEL_OFFICE_AGENT_ROLE = os.getenv("PIXEL_OFFICE_AGENT_ROLE", "lead")
PIXEL_OFFICE_AGENT_ROLE_LABEL_ZH = os.getenv(
    "PIXEL_OFFICE_AGENT_ROLE_LABEL_ZH",
    "加密情报总控",
)

COS_BUCKET = os.getenv("COS_BUCKET", "")
COS_REGION = os.getenv("COS_REGION", "")
COS_SECRET_ID = os.getenv("COS_SECRET_ID", "")
COS_SECRET_KEY = os.getenv("COS_SECRET_KEY", "")
COS_BASE_URL = os.getenv("COS_BASE_URL", "")
