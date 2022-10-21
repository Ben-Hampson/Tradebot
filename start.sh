#!/bin/sh
echo "Welcome to tradebot 2.2"

printenv > /etc/environment
service cron start
service cron status

python --version
cd /home
echo "Updating database"
python -m src.runners.startup
echo "Starting Telegram bot"
python -m src.telegram_bot