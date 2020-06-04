#!/bin/bash

IMAGE=python-gpio/aarch64

function do_build {
    docker build -t ${IMAGE} .
}

function do_run {
    docker run \
        -d \
        --cap-add SYS_RAWIO \
        --device /dev/mem \
        --device /dev/gpiomem \
        --privileged \
        --restart unless-stopped \
        -e HOSTNAME=raspi3 \
        -v /sys/class/gpio:/sys/class/gpio \
        -v /var/log/gpio_monitor.log:/var/log/gpio_monitor.log \
        --name gpio_monitor \
        ${IMAGE} python3 gpio_monitor.py
}

function do_shell {
    docker run \
        --rm \
        -it \
        --cap-add SYS_RAWIO \
        --device /dev/mem \
        --device /dev/gpiomem \
        --privileged \
        -e HOSTNAME=raspi3 \
        -v /sys/class/gpio:/sys/class/gpio \
        -v /var/log/gpio_monitor.log:/var/log/gpio_monitor.log \
        -v $PWD:/home \
        --name gpio_monitor \
        ${IMAGE}
}

function do_install {
    if [ ! -f /var/log/switch.log ]
    then
        sudo touch /var/log/switch.log
    fi
    if [ ! -f /var/log/gpio_monitor.log ]
    then
        sudo touch /var/log/gpio_monitor.log
    fi
    sudo mkdir -p /usr/local/bin
    sudo install -c -m 755 switch.sh /usr/local/bin/switch.sh
}

task=$1
shift
do_$task $*
