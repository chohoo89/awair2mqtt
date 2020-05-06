# awair2mqtt
AWAIR2MQTT Sensor for Home Assistant 입니다.<br>


<br><br>
## Version history
| Version | Date        | 내용              |
| :-----: | :---------: | ----------------------- |
| v1.0    | 2020.05.06  | First version  |

<br>

## Installation
### Manual
- HA 설치 경로 아래 custom_components 에 파일을 넣어줍니다.<br>
  `<config directory>/custom_components/awair2mqtt/__init__.py`<br>
  `<config directory>/custom_components/awair2mqtt/manifest.json`<br>
- configuration.yaml 파일에 설정을 추가합니다.<br>
- Home-Assistant 를 재시작합니다<br>

<br>

## Usage
### configuration
- HA 설정에 awair2mqtt sensor를 추가합니다.<br>
```yaml
awair2mqtt:
  broker: '[Your mqtt broker IP] or [core-mosquitto(HA)]'
  broker_user: '[Your broker id]'
  broker_pw: '[Your broker password]'
  devices:
    - awair_ip: '[Your AWAIR Device IP]'
      awair_id: '[Your AWAIR Device ID]'
      awair_type: '[Your AWAIR Device Model Code]'
```
<br><br>
### 기본 설정값

|옵션|내용|
|--|--|
|broker| (필수) MQTT Broker IP  |
|broker_user| (필수) MQTT Broker ID |
|broker_pw| (필수) MQTT Broker Password |
|broker_port| (옵션) MQTT Broker Port / default(1883) |
|devices| (필수) AWAIR Devices |
|client| (옵션) MQTT Client ID / default(awair2mqtt) |
|scan_interval| (옵션) Sensor Update Term |

<br>

### devices 설정값

|옵션|값|
|--|--|
|awair_ip| (필수) AWAIR Local IP |
|awair_id| (필수) AWAIR ID, 띄워쓰기(X), 한글(X) |
|awair_type| (필수) AWAIR Model Code : S/O/M/E |

<br>

### awair_type 설정값

|코드|값|Score|Temperature|Humidity|VOC|CO2|PM2.5|Light|Noise|
|--|--|--|--|--|--|--|--|--|--|
|S| 2nd Edition |O|O|O|O|O|O|X|X|
|M| Mint |O|O|O|O|X|O|O|O|
|O| Omni |
|E| Element |

<br>
