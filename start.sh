#!/bin/sh
echo "Welcome to tradebot 2.2"
service cron start
service cron status
which python3
python3 --version
echo "Updating database"
python3 /tmp/src/startup.py
echo "Starting server"
python3 /tmp/src/app.py