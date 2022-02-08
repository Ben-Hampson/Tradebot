import telegram
import re
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import logging
from decouple import config

bot = telegram.Bot(token=config('TELEGRAM_TOKEN'))
updater = Updater(token=config('TELEGRAM_TOKEN'), use_context=True)
dispatcher = updater.dispatcher

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)

# /start
def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Hello, I am tradebot!")
start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

# Echo
def echo(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)
echo_handler = MessageHandler(Filters.text & (~Filters.command), echo)
dispatcher.add_handler(echo_handler)

# Formatter
def formatter(text):
    text = re.sub(r'([\[\]()~`>#+-=|{}.!])', r"\\\1", text)
    return text

# Outbound Messages
def outbound(message):
    message = formatter(message)
    bot.send_message(chat_id=config('TELEGRAM_CHAT_ID'), text=message, parse_mode=telegram.ParseMode.MARKDOWN_V2)
outbound_handler = MessageHandler(Filters.text & (~Filters.command), outbound)
dispatcher.add_handler(outbound_handler)

if __name__ == '__main__':
    updater.start_polling()