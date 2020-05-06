""""
Home Assistant component for accessing the AWAIR Local API.
    Adapted furthermore using MQTT messages using HA-discovery to create separate sensors.

Configuration (example):
awair2mqtt:
  broker: mqtt broker IP
  broker_user: mqtt broker login
  broker_pw: mqtt broker password
  broker_port: mqtt broker port

  awair_ip: your AWAIR device IP
  awair_id: your AWAIR deivce Identifiers
  awair_type: your AWAIR Model (S:2nd Edition, O:Omni, M:Mint, E:Element)

  client: MQTT cient-id (optional, default is 'awair2mqtt')
  scan_interval: 150 (optional, default is 300 seconds, keep to 300 seconds or less!)
"""

import json
import logging
import time
from datetime import datetime, timedelta
import requests
import logging
import voluptuous as vol
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt

from homeassistant.const import (
    CONF_PASSWORD, CONF_USERNAME,
    CONF_SCAN_INTERVAL, EVENT_HOMEASSISTANT_STOP)
from homeassistant.helpers.event import async_track_time_interval
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity

__version__ = '1.0.0'

_LOGGER = logging.getLogger(__name__)

CONF_BROKER          = 'broker'
CONF_BROKER_USERNAME = 'broker_user'
CONF_BROKER_PASSWORD = 'broker_pw'
CONF_BROKER_PORT     = 'broker_port'

CONF_DEVICES         = 'devices'

CONF_AWAIR_IP   = 'awair_ip'
CONF_AWAIR_ID   = 'awair_id'
CONF_AWAIR_TYPE = 'awair_type'

CONF_CLIENT   = 'awair2mqtt'

DEFAULT_BROKER_PORT = 1883

DEFAULT_CL = 'awair2mqtt'
DOMAIN     = 'awair2mqtt'

AIRDATA_URL  = 'http://{}/air-data/latest'
SETTINGS_URL = 'http://{}/settings/config/data'

_AWAIR_MODEL = {
  'S': '2nd Edition',
  'O': 'Omni',
  'M': 'Mint',
  'E': 'Element'
}


# AWAIR Properties
_AWAIR_PROP ={
  'score': ['Score',       '',      'mdi:periodic-table',     '{{ value_json.score }}'],
  'temp' : ['Temperature', '°C',    'mdi:thermometer',        '{{ value_json.temp }}'],
  'humid': ['Humidity',    '%',     'mdi:water-percent',      '{{ value_json.humid }}'],
  'voc'  : ['VOC',         'ppb',   'mdi:chemical-weapon',    '{{ value_json.voc }}'],
  'co2'  : ['CO2',         'ppm',   'mdi:periodic-table-co2', '{{ value_json.co2 }}'],
  'pm25' : ['PM2.5',       '㎍/㎥', 'mdi:blur',               '{{ value_json.pm25 }}'],
  'lux'  : ['Light',       'lux',   'mdi:weather-sunny',      '{{ value_json.lux }}'],
  'spl_a': ['Noise',       'dBA',   'mdi:volume-vibrate',     '{{ value_json.spl_a }}'],
  'device_uuid': ['Device UUID', '', 'mdi:devices',           '{{ value_json.device_uuid }}'],
  'wifi_mac'   : ['Wifi MAC',    '', 'mdi:wifi',              '{{ value_json.wifi_mac }}'],
  'ssid'       : ['SSID',        '', 'mdi:wifi',              '{{ value_json.ssid }}'], 
  'ip'         : ['IP',          '', 'mdi:ip',                '{{ value_json.ip }}'],
  'netmask'    : ['Netmask',     '', 'mdi:alpha-m-box',       '{{ value_json.netmask }}'],
  'gateway'    : ['Gateway',     '', 'mdi:alpha-g-box',       '{{ value_json.gateway }}'],
  'fw_version' : ['Firmware',    '', 'mdi:alpha-f-box',       '{{ value_json.fw_version }}'],
  'timezone'   : ['Timezone',    '', 'mdi:alpha-t-box',       '{{ value_json.timezone }}'],
  'display'    : ['Display',     '', 'mdi:alpha-d-box',       '{{ value_json.display }}'],
  'led'        : ['LED',         '', 'mdi:alpha-l-box',       '{{ value_json.led }}' ]
}


REGISTERED = 0
SCAN_INTERVAL = timedelta(seconds=120)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_BROKER): cv.string,
        vol.Required(CONF_BROKER_USERNAME): cv.string,
        vol.Required(CONF_BROKER_PASSWORD): cv.string,
        vol.Optional(CONF_BROKER_PORT, default=DEFAULT_BROKER_PORT): cv.port,
        vol.Required(CONF_DEVICES): vol.All(cv.ensure_list, [{
            vol.Required(CONF_AWAIR_IP): cv.string,
            vol.Required(CONF_AWAIR_ID): cv.string,
            vol.Required(CONF_AWAIR_TYPE): cv.string,
        }]),
        vol.Optional(CONF_CLIENT, default=DEFAULT_CL): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL):
            cv.time_period,
    }),
}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass, config):
    """Initialize the AWAIR to MQTT """
    conf   = config[DOMAIN]

    broker      = conf.get(CONF_BROKER)
    broker_user = conf.get(CONF_BROKER_USERNAME)
    broker_pw   = conf.get(CONF_BROKER_PASSWORD)
    broker_port = conf.get(CONF_BROKER_PORT)

    devices    = conf.get(CONF_DEVICES)

    client        = conf.get(CONF_CLIENT)
    scan_interval = conf.get(CONF_SCAN_INTERVAL)

    client_id = client
    auth = {'username':broker_user, 'password':broker_pw}

    port = broker_port
    keepalive = 60

    async def async_get_awair_data(event_time):
        """Get the topics from the AWAIR API and send to the MQTT Broker."""

        def getAirData(ip):

            result = {}

            try:
                url = AIRDATA_URL.format(ip)

                response = requests.get(url, timeout=10)
                response.raise_for_status()

                awair = response.json()

                return awair

            except Exception as ex:
               _LOGGER.error('Failed to get AWAIR AIR-DATA status Error: %s', ex)
               raise

            return result

        def getSettings(ip):

            result = {}

            try:
               url = SETTINGS_URL.format(ip)

               response = requests.get(url, timeout=10)
               response.raise_for_status()

               settings = response.json()

               return settings

            except Exception as ex:
               _LOGGER.error('Failed to get AWAIR SETTINGS DATA status Error: %s', ex)
               raise

            return result

        def getPayload(id, airdata, settings, device):
            payload  = {}

            data = {}

            for key, value in airdata.items():
                data[key] = value

                tmp = {}
                tmp['name']           = 'awair_{}_{}'.format(id, key)
                tmp['unit_of_meas']   = _AWAIR_PROP[key][1]
                tmp['value_template'] = _AWAIR_PROP[key][3]
                tmp['icon']           = _AWAIR_PROP[key][2]
                tmp['state_topic']    = 'awair/{}/sensors'.format(id)
                tmp['unique_id']      = 'awair_{}_{}'.format(id, key)
                tmp['device']         = device

                payload[key] = tmp

            for key, value in settings.items():
                data[key] = value

                tmp = {}
                tmp['name']           = 'awair_{}_{}'.format(id, key)
                tmp['value_template'] = _AWAIR_PROP[key][3]
                tmp['icon']           = _AWAIR_PROP[key][2]
                tmp['state_topic']    = 'awair/{}/sensors'.format(id)
                tmp['unique_id']      = 'awair_{}_{}'.format(id, key)
                tmp['device']         = device

                payload[key] = tmp

            payload['data'] = data

            return payload


        def getPayloadDevice(id, model, settings):

            # device
            device = {}

            device['identifiers']  = settings['device_uuid']
            device['name']         = 'AWAIR_{}'.format(id)
            device['model']        = 'AWAIR {}'.format(model)
            device['manufacturer'] = 'AWAIR'
            device['sw_version']     = settings['fw_version']

            return device


        """Get the topic-data from the AWAIR API and send to the MQTT Broker."""
        _LOGGER.debug("update called.")

        global REGISTERED

        awair2pub = {}

        for awairdevice in devices:
            aId = awairdevice[CONF_AWAIR_ID]
            aIp = awairdevice[CONF_AWAIR_IP]
            model = _AWAIR_MODEL[awairdevice[CONF_AWAIR_TYPE]]

            # air-data/latest
            airdata = getAirData(aIp)

            # settings/config/data
            config  = getSettings(aIp)

            device = getPayloadDevice(aId, model, config)
            pData  = getPayload(aId, airdata, config, device)

            awair2pub[aId] = pData

        if REGISTERED == 0:
            for id, value in awair2pub.items():
                if ( id is not None and value is not None ):
                    data = pData['data']

                    for item, val in data.items():
                        if ( item is not None and val is not None ):
                            payload = json.dumps(pData[item])
                            publish.single('homeassistant/sensor/awair/{}_{}/config'.format(id, item), payload, qos=0, retain=True, hostname=broker, port=port, auth=auth, client_id=client, protocol=mqtt.MQTTv311)

        REGISTERED = 1

        for id, value in awair2pub.items():
            if ( id is not None, value is not None ):
                data = pData['data']

                payload = json.dumps(data)
                payload = payload.replace(": ", ":")
                publish.single('awair/{}/sensors'.format(id), payload, qos=0, retain=True, hostname=broker, port=port, auth=auth, client_id=client, protocol=mqtt.MQTTv311)

    async_track_time_interval(hass, async_get_awair_data, scan_interval)

    return True
