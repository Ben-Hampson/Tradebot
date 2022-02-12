#!/bin/sh
echo "Welcome to tradebot 2.2"
service cron start
service cron status
poetry run python --version
echo "Updating database"
poetry run python ./src/startup.py
echo "Starting Telegram bot"
poetry run python ./src/telegram_bot.py
echo "Starting server"
poetry run python ./src/app.py