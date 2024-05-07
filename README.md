<p align="center">
  <img src="./docs/icons/elu_charger-transformed.png" alt="Logo" width="300">
</p>

<img src="https://img.shields.io/badge/release-v1.0-blue"/>

# ELU Twins 
This is the open-source version of our product: ELU Twins. The goal is to allow users to simulate charging sessions and driving behavior enabling
easier testing and demoing for e-mobility software such as a charge management system. 

## Disclaimar
We decide to open-source our project to allow our customers to run it locally. Our **main** priority is on releasing new features and not on making it stable. This means that you may encounter issues and bugs. 

# Description
ELU Twins emulate devices related with electro mobility. With this project, it is possible to create virtual chargers (OCPP) and vehicles in seconds. Below is an overview of what has been implemented in the project so far.

### OCPP 1.6

- Core (Done)
- Firmware Management (Done)
- Local Auth List Management (Done)
- Reservation (Not Done)
- Smart Charging (Semi Done)
- Remote Trigger (Done)
- 

### OCPP 2.0.1

- Currently under development, the OCPP 2.0.1 version is not yet fully implemented, but we're working on it.

### Install and build

#### Pre-requisites
The project can be be built using ether docker or natively.

#### With Docker

Docker must be installed.
We suggest to build and run this project using docker, this can be done as follows:

```shell
docker-compose up --build 
```

### What is running with docker-compose
After docker-compose is executed, the following services will be started:
1. Public API: this API expose user interactions, see interactive documentation [here](http://127.0.0.1:8000/docs)
2. Private API: this API exposes internal actions, see interactive documentation [here](http://127.0.0.1:8800/docs)
3. Charge point flower: (http://localhost:5555/) - Open source tool to manage Celery clusters, see [here](https://flower.readthedocs.io/en/latest/) for more information
4. Charge point celery: Simulated charge point using OCPP, using Celery, see [here](https://docs.celeryq.dev/en/stable/#)
5. Csmsv2: CSMS for OCPP 2.0.1
6. csmsv16: CSMS for OCPP 1.6
7. Redis:
8. DB: postgres

### Examples of how to use the API
Step 1 create a user and token and step 2 generate a vehicle and charger, step 3 connect a charger and start a charging session
Create API token
#### Step 1 - How to create a user and token

```python
import requests

# create user
headers = {
'accept': 'application/json',
'Content-Type': 'application/json',
}
json_data = {
    'username': user,
    'password': password,
}
create_user_url = 'http://localhost:8800/user/'
response = requests.post(create_user_url, headers=headers, json=json_data)

# create token

data = {
    'grant_type': '',
    'username': user,
    'password': password,
    'scope': '',
    'client_id': '',
    'client_secret': '',
}
token_url = 'http://localhost:8000/token'

response = requests.post(token_url, headers=headers, data=data)
token = response.json().get("access_token")
```

#### Step 2 - How to create a vehicles and chargers
##### create vehicles
```python
import requests 

headers = {'accept': 'application/json',
 'Authorization': 'Bearer **insert token from step 1 here**',
 'Content-Type': 'application/json'}

# create vehicle
json_data = {
            'name': 'BMW I3',
            'battery_capacity': 65,
            'maximum_charging_rate': 50
        }
vehicle_url = "http://localhost:8000/twin/vehicle/"

response = requests.post(vehicle, headers=headers, json=json_data)
```
If successful, the returned response is 

```
{'created_at': '2024-05-06T06:30:56.568111',
 'updated_at': '2024-05-06T06:30:56.568177',
 'name': 'BMW I3',
 'id_tag_suffix': 'NEAKPLTYIK',
 'battery_capacity': 65,
 'maximum_dc_charging_rate': 50,
 'maximum_ac_charging_rate': 50,
 'soc': 10.0,
 'status': 'ready-to-charge',
 'id': '1140b70f-9971-41b6-bd70-8a59e4242002',
 'transaction_id': None}
```

##### create charger
```python
import requests 

headers = {'accept': 'application/json',
 'Authorization': 'Bearer **insert token from step 1 here**',
 'Content-Type': 'application/json'}
json_data = {
              "name": "Terra180",
              "maximum_dc_power": 180,
              "maximum_ac_power": 20,
              "csms_url": "ws://csms:9000",
              "evses": [
                  {"connectors":[{"connector_type": "cCCS1"}]}, 
                  {"connectors":[{"connector_type": "cCCS1"}]}]
            }
charger = "http://localhost:8000/twin/charge-point/"

response = requests.post(charger, headers=headers, json=json_data)

```
If successful, the returned response is 
```json
{'name': 'Marseille charger 0',
 'cid': 'ELU-WIU4-KNKTT-821XH28NUWB',
 'vendor': 'Elu Twin',
 'model': 'Digital Twin',
 'password': '1234',
 'csms_url': 'ws://csms:9000',
 'ocpp_protocol': 'ocpp1.6',
 'boot_reason': None,
 'voltage_ac': 230,
 'voltage_dc': 400,
 'maximum_dc_power': 150,
 'maximum_ac_power': 20,
 'status': 'Unavailable',
 'charge_point_task_id': None,
 'last_heartbeat': None,
 'token_cost_per_minute': 2,
 'id': '425d8189-746c-4295-a57d-8ed1e89ccc75',
 'quota_id': '2e87f9e3-a789-4254-b29e-1a2b2d293ba5',
 'ocpp_configuration_v16_id': '07c13e4b-ceea-4167-8017-7c3fc5efb612',
 'created_at': '2024-05-06T06:31:00.583905',
 'updated_at': '2024-05-06T06:31:00.583943',
 'evses': [{'created_at': '2024-05-06T06:31:00.591886',
   'updated_at': '2024-05-06T06:31:00.591911',
   'id': 'bbf1820b-e2d9-4c85-9746-8169df2d0c12',
   'evseid': 1,
   'status': 'unavailable',
   'active_connector_id': None,
   'connectors': [{'created_at': '2024-05-06T06:31:00.596059',
     'updated_at': '2024-05-06T06:31:00.596073',
     'id': '7da880c2-604e-4980-ba06-0683daf0672d',
     'connectorid': 1,
     'status': 'unavailable',
     'current_dc_power': 0,
     'current_dc_current': 0,
     'current_dc_voltage': 0,
     'current_ac_power': 0,
     'current_ac_current': 0,
     'current_ac_voltage': 0,
     'current_energy': 0.0,
     'total_energy': 0.0,
     'soc': None,
     'connector_type': 'cCCS1',
     'id_tag': None,
     'transactionid': None,
     'queued_action': [],
     'transaction_id': None,
     'vehicle_id': None}]},
  {'created_at': '2024-05-06T06:31:00.598812',
   'updated_at': '2024-05-06T06:31:00.598820',
   'id': 'b1eaca84-d9ce-4f50-b4d0-972daa38834d',
   'evseid': 2,
   'status': 'unavailable',
   'active_connector_id': None,
   'connectors': [{'created_at': '2024-05-06T06:31:00.600922',
     'updated_at': '2024-05-06T06:31:00.600943',
     'id': '2ea0591c-5546-4486-9a75-62f62a0a9704',
     'connectorid': 2,
     'status': 'unavailable',
     'current_dc_power': 0,
     'current_dc_current': 0,
     'current_dc_voltage': 0,
     'current_ac_power': 0,
     'current_ac_current': 0,
     'current_ac_voltage': 0,
     'current_energy': 0.0,
     'total_energy': 0.0,
     'soc': None,
     'connector_type': 'cCCS1',
     'id_tag': None,
     'transactionid': None,
     'queued_action': [],
     'transaction_id': None,
     'vehicle_id': None}]}],
 'user_id': '52ca0620-a51a-4233-bd16-4250b163ca06'}
```

#### How to create a charger add output
```python
import requests 

headers = {'accept': 'application/json',
 'Authorization': 'Bearer **insert token here**',
 'Content-Type': 'application/json'}


json_data = {
              "name": "Terra180",
              "maximum_dc_power": 180,
              "maximum_ac_power": 20,
              "csms_url": "ws://csms:9000",
              "evses": [
                  {"connectors":[{"connector_type": "cCCS1"}]}, 
                  {"connectors":[{"connector_type": "cCCS1"}]}]
            }
charger = "http://localhost:8000/twin/charge-point/"

response = requests.post(charger, headers=headers, json=json_data)
```

#### Further examples
You can check out the jupyter notebook found under [here](notebooks/quick_start_api.ipynb) or check out the interactive interactive API documentation:
- Public API: (http://127.0.0.1:8000/docs)
- Private API: (http://127.0.0.1:8800/docs)


## Next steps
- Increase coverage

## How to contribute

We welcome contributions from everyone who is willing to improve this project. Whether you're fixing bugs, adding new features, improving documentation, or suggesting new ideas, your help is greatly appreciated! Just make sure you follow these simple guidelines before opening up a PR:
- Follow the [Code of Conduct](CODE_OF_CONDUCT.md): Always adhere to the Code of Conduct and be respectful of others in the community.
- Test Your Changes: Ensure your code is tested and as bug-free as possible.
- Update Documentation: If you're adding new features or making changes that require it, update the documentation accordingly.

