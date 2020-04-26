#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#        @file: switch.py
#
# @description: setting/getting the state of relays connected to GPIO pins
#               state is written to /var/log/switch.log
#
#    @requires: RPi.GPIO modules, requests
#
#      @author: Alexander Fischer
#
#  @lastChange: 2019-10-24
#
#
import argparse
import datetime
import logging
import logging.config
import os
import subprocess
import sys
import time

import requests

hasGpio = False
try:
    import RPi.GPIO as GPIO  # Import GPIO library
    hasGpio = True
except:
    pass

def check_host(host):
    log.debug('checking host {0}'.format(host))
    return os.system('ping -q -c 1 ' + host) == 0

def set_iobroker_values(host, values):
    """
    Set ioBroker object values.
    """
    log.debug('set_iobroker_values() start')
    result = False
    if len(values) > 0:
        try:
            response = requests.post('http://' + host + ':8082/setBulk/?' + '&'.join(values))
            result = response.status_code == 200
            log.info('{0} values sent to ioBroker on {1}'.format(len(values), host))
        except:
            log.critical('ioBroker connection to {0} failed'.format(host))
            pass
    log.debug('set_iobroker_values() finish')
    return result

if 'HOSTNAME' in os.environ.keys():
    hostname = os.environ['HOSTNAME']
else:
    hostname = subprocess.Popen('hostname', stdout=subprocess.PIPE).stdout.read().strip()
hostname = hostname.lower()

parser = argparse.ArgumentParser(description='GPIO switch command line tool')
parser.add_argument('-c', '--check', nargs=1, default=[''], help='check another host/IP before turning switch')
parser.add_argument('-d', '--debug', action='store_true', help='debug execution')
parser.add_argument('-H', '--host', nargs=1, default=['localhost'], help='execute script on remote host/IP')
parser.add_argument('-i', '--iobroker', default='192.168.137.83', help='ioBroker hostname/IP (192.168.137.83)')
parser.add_argument('-t', '--test', action='store_true', help='test mode (no switch action takes place)')
parser.add_argument('-v', '--verbose', type=int, default=0, help='verbosity (0)')
parser.add_argument('switch', type=int, help='the switch to set: 0|1|...')
parser.add_argument('state', nargs='?', default=None, help='the state of the switch: on|off')
args = parser.parse_args(sys.argv[1:])

self = os.path.basename(sys.argv[0])
myName = os.path.splitext(self)[0]
log = logging.getLogger(myName)
logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
if args.debug:
    log.setLevel(logging.DEBUG)
else:
    log.setLevel(logging.INFO)

log.debug('ARGS: {0}'.format(args))

if args.host[0] != 'localhost':
    if not check_host(args.host[0]):
        log.error('ERROR: host {0} not alive'.format(args.host[0]))
        quit()
    # copy yourself to the remote host and execute there
    log.debug('transferring to host {0}'.format(args.host[0]))
    cmd = 'scp {0} pi@{1}:/var/tmp'.format(sys.argv[0], args.host[0])
    os.system(cmd)
    cmd = 'ssh pi@{0} sudo /var/tmp/{1} --iobroker {2} {3}'.format(args.host[0], os.path.basename(sys.argv[0]), args.iobroker, args.switch)
    if args.state != None:
       cmd += ' ' + args.state
    os.system(cmd)
    quit()

if not hasGpio:
    log.error('RPi.GPIO library not present')
    quit()

GPIO.setwarnings(False)
# RPi.GPIO Layout verwenden (wie Pin-Nummern)
GPIO.setmode(GPIO.BCM)

pinOut = []
if hostname == 'raspi2':
    pinOut = [ 18, 24 ]
elif hostname == 'raspi3':
    pinOut = [ 12, 16, 20, 21 ]
elif hostname == 'raspi5':
    pinOut = [ 18, 24 ]

for pin in pinOut:
    log.debug('GPIO setup pin {0}'.format(pin))
    GPIO.setup(pin, GPIO.OUT)

switchOut = args.switch   # 0, 1
if int(switchOut) >= 0 and int(switchOut) < len(pinOut):
    pin = pinOut[int(switchOut)]
else:
    log.error('switch {0} not available'.format(switchOut))
    quit()

state = { 0 : 'on', 1 : 'off' }
turnSwitch = True
if args.check[0]:
    turnSwitch = not check_host(args.check[0])
if args.state != None:
    if turnSwitch:
        switchValue = args.state # on, off
        # default is off
        value = 1
        if switchValue == 'on':
            value = 0
        if not args.test:
            log.debug('GPIO output pin {0} = {1}'.format(pin, value))
            GPIO.output(pin, value)
        if args.iobroker != 'none':
            binaryState = { 0 : 'false', 1 : 'true' }
            cmd = 'javascript.0.switch.{0}.relay{1}.state={2}'.format(hostname, switchOut, binaryState[1-value])
            log.debug(cmd)
            set_iobroker_values(args.iobroker, [ cmd ])
else:
    log.info('{0} pin {1} {2}'.format(hostname, pin, state[GPIO.input(pin)]))

msg = 'relay {0} = {1}'.format(switchOut, state[GPIO.input(pin)])
if args.test:
    if args.check[0]:
        log.info('check {0} -> {1}'.format(args.check[0], turnSwitch))
    log.info(msg)
else:
    with open('/var/log/switch.log', 'a') as f:
        f.write(datetime.datetime.now().isoformat(' ').split('.')[0] + ' ' + msg + '\n')
