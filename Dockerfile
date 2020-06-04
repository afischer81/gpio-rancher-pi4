FROM seblucas/alpine-python3 AS base

FROM base AS builder

RUN mkdir /install
WORKDIR /install
COPY requirements.txt /tmp/requirements.txt

RUN apk update && \
    apk add --no-cache alpine-sdk python3-dev autoconf automake make wiringpi-dev && \
    pip3 install --no-cache-dir --install-option="--prefix=/install" -r /tmp/requirements.txt

RUN git clone https://github.com/technion/lol_dht22 && \
    cd lol_dht22 && \
    ./configure && \
    aclocal && \
    autoconf && \
    automake && \
    make && \
    mkdir -p /install/local/bin && \
    mv ./loldht /install/local/bin && \
    strip /install/local/bin/loldht

FROM base
COPY --from=builder /install /usr
RUN apk add wiringpi

WORKDIR /home
COPY switch.py /home
COPY gpio_monitor.py /home
