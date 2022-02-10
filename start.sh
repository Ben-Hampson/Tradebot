#!/bin/sh
echo "Welcome to tradebot 2.2"
service cron start
service cron status
poetry run python --version
echo "Updating database"
poetry run python /home/src/startup.py
echo "Starting server"
poetry run python /home/src/app.py