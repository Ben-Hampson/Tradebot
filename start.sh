#!/bin/sh
echo "Welcome to tradebot 2.2"

printenv > /etc/environment
service cron start
service cron status

python --version
cd /home/src
echo "Updating database"
python ./startup.py
echo "Starting Telegram bot"
python ./telegram_bot.py
echo "Starting server"
python ./app.py