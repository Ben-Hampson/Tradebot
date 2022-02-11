FROM python:3.8

# Set Env vars
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/London

WORKDIR /home

# Install any Python package requirements
COPY src/ ./src
RUN mkdir -p /home/data \
    && mkdir -p /home/logs

# Cron
ENV PATH="/root/.local/bin:$PATH"
RUN apt-get -qq update -y && apt-get -qq install -y cron curl \
    && curl -sSL https://install.python-poetry.org | python3 -
COPY root /etc/cron.d/root
RUN chmod 0644 /etc/cron.d/root
RUN crontab /etc/cron.d/root

# start.sh
COPY /start.sh .
RUN chmod +x ./start.sh

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-dev

CMD ["/bin/bash", "/home/start.sh"]