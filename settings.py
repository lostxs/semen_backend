from zoneinfo import ZoneInfo

from envparse import Env

env = Env()

ekb_timezone = ZoneInfo("Asia/Yekaterinburg")

DATABASE_URL = env.str(
    "DATABASE_URL", default="postgresql+asyncpg://postgres:1234@localhost/webdb"
)
REDIS_URL = env.str("REDIS_URL", default="redis://localhost")


SECRET_KEY = env.str("SECRET_KEY", default="My_secret")
ALGORITHM: str = env.str("ALGORITHM", default="RS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = env.int("ACCESS_TOKEN_EXPIRE_MINUTES", default=30)

ACTIVATION_CODE_EXPIRE_MINUTES: int = env.int(
    "ACTIVATION_CODE_EXPIRE_MINUTES", default=10
)
