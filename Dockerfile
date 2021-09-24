FROM ubuntu:focal

ENV DEBIAN_FRONTEND=noninteractive \
    REDIS_HOST=redis \
    APP_PATH=/opt/src/app \
    DATA_VOLUME=/data

RUN apt-get update && \
    apt-get install -y \
    build-essential \
    python3 \
    python3-dev \
    libssl-dev \
    python-protobuf \
    libleveldb-dev \
    git \
    wget \
    ffmpeg \
    python3-pip \
    sqlite3 \
    webp \
    supervisor \
    unzip

WORKDIR /opt/src/lbrynet
RUN git clone https://github.com/lbryio/lbry-sdk.git
WORKDIR /opt/src/lbrynet/lbry-sdk
RUN sed -i 's/aiohttp==3.5.4/aiohttp==3.6.2/' setup.py
RUN make install

COPY scripts/requirements.txt ./requirements.txt
RUN mkdir -p /var/log/supervisor && \
    pip install -r ./requirements.txt

COPY scripts/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY scripts/daemon_settings.yml /root/daemon_settings.yml
COPY scripts/start.sh /root/start.sh

WORKDIR $APP_PATH
ADD app $APP_PATH

EXPOSE 5279 3000

CMD /root/start.sh
