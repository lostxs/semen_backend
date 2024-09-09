from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from envparse import Env

load_dotenv(dotenv_path=".env",override=True)
env = Env()

ekb_timezone = ZoneInfo("Asia/Yekaterinburg")


DATABASE_URL: str = env.str("DATABASE_URL")
REDIS_URL: str = env.str("REDIS_URL")


SECRET_KEY: str = env.str("SECRET_KEY")
ALGORITHM: str = env.str("ALGORITHM", default="HS256")

SMTP_USER: str = env.str("SMTP_USER")
SMTP_PASSWORD: str = env.str("SMTP_PASSWORD")
SMTP_HOST: str = env.str("SMTP_HOST")
SMTP_PORT: int = env.int("SMTP_PORT")


ACCESS_TOKEN_EXPIRE_MINUTES: int = env.int("ACCESS_TOKEN_EXPIRE_MINUTES")
CHAT_TOKEN_EXPIRE_MINUTES: int = env.int("CHAT_TOKEN_EXPIRE_MINUTES")
ACTIVATION_CODE_EXPIRE_MINUTES: int = env.int("ACTIVATION_CODE_EXPIRE_MINUTES")

print(f"CHAT_TOKEN_EXPIRE_MINUTES: {CHAT_TOKEN_EXPIRE_MINUTES}")
print(f"ACCESS_TOKEN_EXPIRE_MINUTES: {ACCESS_TOKEN_EXPIRE_MINUTES}")
print(f"ACTIVATION_CODE_EXPIRE_MINUTES: {ACTIVATION_CODE_EXPIRE_MINUTES}")