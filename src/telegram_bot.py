"""Telegram bot. Sends messages and handles commands."""

import logging
import os
import re

import telegram
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)

bot = telegram.Bot(token=os.getenv("TELEGRAM_TOKEN"))
updater = Updater(token=os.getenv("TELEGRAM_TOKEN"), use_context=True)
dispatcher = updater.dispatcher

def start(update, context):
    """For command '/start', return a message."""
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Hello, I am tradebot!"
    )

def formatter(text: str) -> str:
    """Format messages to make sure they don't cause an error."""
    text = re.sub(r"([\[\]()~`>#+-=|{}.!])", r"\\\1", text)
    return text


def outbound(message: str):
    """Send a Telegram message."""
    message = formatter(message)
    bot.send_message(
        chat_id=os.getenv("TELEGRAM_CHAT_ID"),
        text=message,
        parse_mode=telegram.ParseMode.MARKDOWN_V2,
    )


outbound_handler = MessageHandler(Filters.text & (~Filters.command), outbound)
dispatcher.add_handler(outbound_handler)


def main():
    """Run Telegram bot."""
    start_handler = CommandHandler("start", start)
    dispatcher.add_handler(start_handler)

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
