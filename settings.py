from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from envparse import Env

load_dotenv()
env = Env()

ekb_timezone = ZoneInfo("Asia/Yekaterinburg")


DATABASE_URL = env.str("DATABASE_URL")
REDIS_URL = env.str("REDIS_URL")


SECRET_KEY = env.str("SECRET_KEY")
ALGORITHM: str = env.str("ALGORITHM", default="HS256")


ACCESS_TOKEN_EXPIRE_MINUTES: int = env.int("ACCESS_TOKEN_EXPIRE_MINUTES", default=30)
CHAT_TOKEN_EXPIRE_MINUTES: int = env.int("CHAT_TOKEN_EXPIRE_MINUTES", default=30)

ACTIVATION_CODE_EXPIRE_MINUTES: int = env.int("ACTIVATION_CODE_EXPIRE_MINUTES", default=10)
