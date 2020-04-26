#!/bin/bash

IMAGE=python-gpio/aarch64

function do_build {
    docker build -t ${IMAGE} .
}

function do_run {
    # TODO: not yet working
    docker run --rm -it \
        --device /dev/mem \
        --device /dev/gpiomem \
        -e HOSTNAME=raspi3 \
        -v /var/log/gpio_monitor.log:/var/log/gpio_monitor.log \
        --name gpio_monitor \
        ${IMAGE}
#        --restart unless-stopped \
}

function do_install {
    if [ ! -f /var/log/switch.log ]
    then
        sudo touch /var/log/switch.log
    fi
    sudo mkdir -p /usr/local/bin
    sudo install -c -m 755 switch.sh /usr/local/bin/switch.sh
}

task=$1
shift
do_$task $*
