#!/usr/bin/env python
# -*- coding: utf-8 -*-

# python modules
from __future__ import unicode_literals
from __future__ import print_function

import copy
import datetime
import logging
import logging.config
import os
import subprocess
import sys
import threading
import time

import RPi.GPIO as GPIO  # Import GPIO library

hasRequests = False
try:
    import requests
    hasRequests = True
except:
    pass

self = os.path.basename(sys.argv[0])
myName = os.path.splitext(self)[0]
logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger(myName)
log.setLevel(logging.INFO)

if 'HOSTNAME' in os.environ.keys():
    hostname = os.environ['HOSTNAME']
else:
    hostname = subprocess.Popen('hostname', stdout=subprocess.PIPE).stdout.read().strip()
hostname = hostname.lower()

sensors = dict()
state = dict()
ioBrokerHost = ''

if hostname == 'raspi1':
    # gpio sensor definition: gpio:pin = in|out:up|down:both|rising|falling:time
    sensors['gpio:12'] = 'in:up:both:500'
    sensors['gpio:20'] = 'in:up:both:500'
    sensors['gpio:21'] = 'in:up:both:500'
    # sensor states
    state[12] = { 'name' : 'Gaszähler', 'value' : '', 'valueList' : [ 'tick', 'tock' ], 'changed' : False }
    state[20] = { 'name' : 'Waschraum Tür', 'value' : '', 'valueList' : [ 'closed', 'open' ], 'changed' : False }
    state[21] = { 'name' : 'Keller Tür', 'value' : '', 'valueList' : [ 'closed', 'open' ], 'changed' : False }
    ioBrokerHost = 'raspi3'
elif hostname == 'raspi2':
    # gpio sensor definition: gpio:pin = in|out:up|down:both|rising|falling:time
    sensors['gpio:22'] = 'in:up:both:500'
    sensors['gpio:23'] = 'in:up:both:500'
    sensors['gpio:25'] = 'in:up:both:500'
    # sensor states
    state[22] = { 'name' : 'Bewegung', 'value' : '', 'valueList' : [ 'absent', 'present' ], 'changed' : False }
    state[23] = { 'name' : 'Fenster', 'value' : '', 'valueList' : [ 'closed', 'open' ], 'changed' : False }
    state[25] = { 'name' : 'contact23', 'value' : '', 'valueList' : [ 'closed', 'open' ], 'changed' : False }
    ioBrokerHost = 'raspi3'
elif hostname == 'raspi3':
    # gpio sensor definition: gpio:pin = in|out:up|down:both|rising|falling:time
    sensors['gpio:23'] = 'in:up:both:500'
    sensors['gpio:24'] = 'in:up:falling:500'
    # sensor states
    state[23] = { 'name' : 'Aquarium Tür', 'value' : '', 'valueList' : [ 'closed', 'open' ], 'changed' : False }
    state[24] = { 'name' : 'Taste1', 'value' : '', 'valueList' : [ 'pressed', '' ], 'changed' : False }
    ioBrokerHost = 'raspi3'
elif hostname == 'raspi9':
    # gpio sensor definition: gpio:pin = in|out:up|down:both|rising|falling:time
    sensors['gpio:23'] = 'in:up:falling:500'
    sensors['gpio:24'] = 'in:up:falling:500'
    state[23] = { 'name' : 'Taste1', 'value' : '', 'valueList' : [ 'pressed', '' ], 'changed' : False }
    state[24] = { 'name' : 'Taste2', 'value' : '', 'valueList' : [ 'pressed', '' ], 'changed' : False }

def GpioInputChange(pin):
    value = GPIO.input(pin)
    if not pin in state.keys():
        return
    state[pin]['value'] = state[pin]['valueList'][value]
    state[pin]['changed'] = True
    log.info('pin {0} value {1} state {2}, {3}'.format(pin, value, state[pin]['name'], state[pin]['value']))
    sys.stdout.flush()

class IoBroker(threading.Thread):
    def __init__(self, url, values):
        threading.Thread.__init__(self)
        self.url = url
        self.values = values

    def check_host(self, name):
        result = False
        if subprocess.call([ 'ping', '-q', '-n', '-c', '3', '-W', '5', name ]) == 0:
            result = True
        return result

    def run(self):
        """
        Send measurement values to ioBroker, if host is accessible
        """
        ioBrokerHost = 'raspi3'
        #m = re.match('http://([\d\.]+)/.*', self.url)
        #if m:
        #    ioBrokerHost = m.group(1)
        ioBrokerIds = {}
        ioBrokerIds['raspi1:Gaszähler'] = 'javascript.0.contact.reed.1={0}'
        ioBrokerIds['raspi1:Waschraum Tür'] = 'javascript.0.contact.reed.2={0}'
        ioBrokerIds['raspi1:Keller Tür'] = 'javascript.0.contact.reed.3={0}'
        ioBrokerIds['raspi2:Bewegung'] = 'javascript.0.sensor.motion.1={0}'
        ioBrokerIds['raspi2:Fenster'] = 'javascript.0.contact.reed.4={0}'
        ioBrokerIds['raspi2:contact23'] = 'javascript.0.contact.reed.5={0}'
        ioBrokerIds['raspi3:Taste1'] = 'javascript.0.switch.raspi3.relay0.state'
        ioBrokerIds['raspi3:Aquarium Tür'] = 'javascript.0.contact.reed.6={0}'
        ioBrokerValues = []
        ioBrokerToggleValues = []
        valueMap = { 'open' : 'true', 'present' : 'true', 'tock' : 'true' }
        for v in self.values:
            if not v['changed']:
                continue
            name = v['name']
            # map values to 'true' or 'false' (ioBroker types are boolean)
            val = 'false'
            if v['value'] in valueMap.keys():
                val = valueMap[v['value']]
            ioBrokerId = hostname.lower() + ':' + name
            if ioBrokerId in ioBrokerIds.keys():
                if v['value'] == 'pressed':
                    ioBrokerToggleValues.append(ioBrokerIds[ioBrokerId])
                else:
                    ioBrokerValues.append(ioBrokerIds[ioBrokerId].format(val))
        result = False
        if len(ioBrokerValues) > 0:
            if self.check_host(ioBrokerHost):
                try:
                    response = requests.post(self.url + '/setBulk/?' + '&'.join(ioBrokerValues))
                    result = response.status_code == 200
                    log.info('{0} values sent to ioBroker on {1}'.format(len(ioBrokerValues), ioBrokerHost))
                except:
                    log.critical('ioBroker connection to {0} failed'.format(ioBrokerHost))
                    pass
            else:
                log.error('no ioBroker connection to {0}'.format(ioBrokerHost))
        if len(ioBrokerToggleValues) > 0:
            if self.check_host(ioBrokerHost):
                for value in ioBrokerToggleValues:
                    try:
                        response = requests.get(self.url + '/toggle/' + value)
                        result = response.status_code == 200
                        log.info('toggled ioBroker id {0}'.format(value))
                    except:
                        log.critical('ioBroker connection to {0} failed'.format(ioBrokerHost))
                        pass
            else:
                log.error('no ioBroker connection to {0}'.format(ioBrokerHost))
        return result

def InputMonitor():
    gpioDir = { 'in' : GPIO.IN, 'out' : GPIO.OUT }
    gpioPull = { 'down' : GPIO.PUD_DOWN, 'up' : GPIO.PUD_UP }
    gpioEvent = { 'both' : GPIO.BOTH, 'falling' : GPIO.FALLING, 'rising' : GPIO.RISING }

    log.info('start ioBroker={0}'.format(ioBrokerHost))
    if ioBrokerHost and not hasRequests:
        log.error('no requests module, hence no connection to IoBroker host ' + ioBrokerHost)
    # setup sensor pins
    for sens in sensors.keys():
        if not sens.startswith('gpio:'):
            continue
        pin = int(sens.split(':')[-1])
        [ dir, pull, event, bt ] = sensors[sens].split(':')
        dir = gpioDir[dir]
        pull = gpioPull[pull]
        event = gpioEvent[event]
        bt = int(bt)
        
        GPIO.setup(pin, dir, pull_up_down=pull)
        if not 'Taste' in state[pin]['name']:
            # show initial state
            GpioInputChange(pin)
        GPIO.add_event_detect(pin, event, callback=GpioInputChange, bouncetime=bt)

    try:
        while True:
            if hasRequests and ioBrokerHost:
                ioBrokerThread = IoBroker('http://' + ioBrokerHost + ':8082', copy.deepcopy(list(state.values())))
                ioBrokerThread.start()
            for s in state.values():
                s['changed'] = False
            time.sleep(2.0)
    except KeyboardInterrupt:
        pass
    log.info('stop')

GPIO.setmode(GPIO.BCM)
InputMonitor()
GPIO.cleanup()
