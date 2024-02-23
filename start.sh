#!/bin/sh
echo "Welcome to tradebot 2.2"

printenv > /etc/environment
service cron start
service cron status

python --version
cd /home

echo "Checking IBeam container status and authentication."
python -m run.check_ibeam

echo "Updating database"
python -m run.startup

tail -f /dev/null
