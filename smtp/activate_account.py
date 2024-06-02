import logging
import smtplib
import random
from typing import cast
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import ActivationCode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def generate_activation_code(session: AsyncSession):
    while True:
        code = f"{random.randint(100000, 999999)}"
        exist_query = select(ActivationCode).where(cast("ColumnElement[bool]", ActivationCode.code == code))
        result = await session.execute(exist_query)
        if result.scalar_one_or_none() is None:
            return code


async def send_activation_code(email: str, activation_code: str):
    sender_email = "kritden@yandex.ru"
    receiver_email = email
    password = "rvqxwfbjsyrqjocs"

    message = MIMEMultipart("alternative")
    message["Subject"] = "Activation Code"
    message["From"] = sender_email
    message["To"] = receiver_email

    text = f"""\
        Hi,
        Your activation code is {activation_code}"""
    part = MIMEText(text, "plain")
    message.attach(part)

    try:
        server = smtplib.SMTP_SSL("smtp.yandex.ru", 465)
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())
        server.quit()
    except Exception as e:
        logger.info(f"Error sending email: {e}")
