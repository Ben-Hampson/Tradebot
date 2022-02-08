FROM python:3.8

# Set Env vars
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/London

# Install any Python package requirements
COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt
COPY src/ /tmp/src

# Cron
RUN apt-get -qq update -y && apt-get -qq install -y cron
COPY root /etc/cron.d/root
RUN chmod 0644 /etc/cron.d/root
RUN crontab /etc/cron.d/root

# start.sh
COPY /start.sh .
RUN chmod +x /start.sh

CMD ["/bin/bash", "/start.sh"]