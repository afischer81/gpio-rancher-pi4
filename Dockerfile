FROM seblucas/alpine-python3 AS base

FROM base AS builder

RUN mkdir /install
WORKDIR /install
COPY requirements.txt /tmp/requirements.txt

RUN apk update && \
    apk add --no-cache alpine-sdk python3-dev && \
    pip3 install --no-cache-dir --install-option="--prefix=/install" -r /tmp/requirements.txt

#WORKDIR /tmp
#RUN git clone https://github.com/adafruit/Adafruit_Python_DHT.git && \
#    cd Adafruit_Python_DHT && \
#    python3 setup.py install \
#    install -c -m 755 examples/AdafruitDHT.py /install/usr/bin

FROM base
COPY --from=builder /install /usr

WORKDIR /home
COPY switch.py /home
COPY gpio_monitor.py /home
