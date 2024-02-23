#!/bin/sh
echo "Welcome to tradebot 2.2"

printenv > /etc/environment
service cron start
service cron status

python --version
cd /home
echo "Updating database"
python -m run.startup

tail -f /dev/null
