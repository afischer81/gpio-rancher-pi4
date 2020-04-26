#!/bin/bash

THIS_HOST=$(hostname)
IMAGE=python-gpio/aarch64

host=$1
iobroker=$2
switch=$3
state=$4
echo $(date +"%Y-%m-%d %H:%M:%S") INFO switch ${host:=localhost} ${iobroker:=none} ${switch:=0} $state

if [ $host != $THIS_HOST ]
then
    switch_args="-H $host"
fi
switch_args="$switch_args --iobroker $iobroker $switch $state"
case $(ps ax -o pid,comm | head -2 | tail -1 | awk '{ print $2 }') in
    systemd | system-dockerd)
        echo $(date +"%Y-%m-%d %H:%M:%S") INFO running on host $THIS_HOST
        if [ "$THIS_HOST" = "raspi3" ]
        then
            docker run --rm \
                --device /dev/mem \
                --device /dev/gpiomem \
                -e HOSTNAME=raspi3 \
                -v /var/log/switch.log:/var/log/switch.log \
                ${IMAGE} python3 switch.py $switch_args
        else
            sudo /usr/local/bin/switch.py $switch_args
        fi
        ;;
    *)
        echo $(date +"%Y-%m-%d %H:%M:%S") INFO running in container, host $THIS_HOST
        ssh pi@$host /usr/local/bin/switch.sh $host $iobroker $switch $state 
        ;;
esac
