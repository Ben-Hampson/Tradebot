"""Telegram bot. Sends messages and handles commands."""
import logging
import os
import re

import telegram
from telegram.ext import Application

import asyncio

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)


class TelegramBot:
    """Singleton Telegram bot for sending messages and handling commands."""

    _instance = None

    def __new__(cls):
        """Singleton. Return existing instance if there is one, else create a new one."""
        if cls._instance is None:
            cls._instance = super(TelegramBot, cls).__new__(cls)

            cls.application = (
                Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()
            )

        return cls._instance

    def formatter(self, text: str) -> str:
        """Format messages to make sure they don't cause an error."""
        text = re.sub(r"([\[\]()~`>#+-=|{}.!])", r"\\\1", text)
        return text

    def outbound(self, message: str):
        """Send a Telegram message."""
        message = self.formatter(message)
        asyncio.run(
            self.application.bot.send_message(
                chat_id=os.getenv("TELEGRAM_CHAT_ID"),
                text=message,
                parse_mode=telegram.constants.ParseMode.MARKDOWN_V2,
            )
        )
