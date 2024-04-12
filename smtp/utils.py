from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ActivationCode
from settings import ACTIVATION_CODE_EXPIRE_MINUTES


async def delete_expired_activation_codes(db: AsyncSession):
    async with db.begin():
        current_time = datetime.utcnow()
        expired_codes = await db.execute(
            select(ActivationCode).where(
                ActivationCode.created_at
                < current_time - timedelta(hours=ACTIVATION_CODE_EXPIRE_MINUTES)
            )
        )
        for code in expired_codes.scalars().all():
            await db.delete(code)
        await db.commit()
