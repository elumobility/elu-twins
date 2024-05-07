<p align="center">
  <img src="./docs/icons/elu_charger-transformed.png" alt="Logo" width="300">
</p>

<img src="https://img.shields.io/badge/release-v1.0-blue"/>

# ELU Twins 
This is the open-source version of our product: ELU Twins. The goal is to allow users to simulate charging sessions and driving behavior enabling
easier testing and demoing for e-mobility software such as a charge management system. 

# Description
ELU Twins emulate devices related with electro mobility. With this project, it is possible to create virtual chargers (OCPP) and vehicles in seconds. Below is an overview of what has been implemented in the project so far.

## Comments
We open-sourced this project on the 06/06/2024 and it is still work in progress. This means that you may find bugs, missing features, and lack of tests. We are working on improving all of this.

This is a dynamic project and our **main** priority is releasing the project and not on making it stable. This means that you may encounter issues and bugs.

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

### How to run
We suggest to build and run this project using docker, this can be done as follows:

```shell
docker-compose up --build 
```
### What is running with docker-compose
After docker-compose is executed, the following services will be started:
1. Public API: (http://127.0.0.1:8000/docs)
2. Private API: (http://127.0.0.1:8800/docs)
3. Charge point flower: (http://localhost:5555/) - Open source tool to manage Celery clusters, see [here](https://flower.readthedocs.io/en/latest/) for more information
4. Charge point celery: each charger is a different thread using Celery, see [here](https://docs.celeryq.dev/en/stable/#)
5. Csmsv2: CSMS for OCPP 2.0.1
6. csmsv16: CSMS for OCPP 1.6
7. Redis:
8. DB: postgres

### Examples of how to use the API
#### How to create a user

```python
import requests 
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
```
#### How to create a token
```python
import requests 

headers = {
    'accept': 'application/json',
    'Content-Type': 'application/x-www-form-urlencoded',
}

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
```

#### How to create a vehicle
```python
import requests 

{'accept': 'application/json',
 'Authorization': 'Bearer **insert token here**',
 'Content-Type': 'application/json'}


json_data = {
            'name': 'BMW I3',
            'battery_capacity': 65,
            'maximum_charging_rate': 50
        }
vehicle_url = "http://localhost:8000/twin/vehicle/"

response = requests.post(vehicle, headers=headers, json=json_data)
```

#### How to create a charger
```python
import requests 

{'accept': 'application/json',
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
- Add tests
- Add coverage

## How to contribute

We welcome contributions from everyone who is willing to improve this project. Whether you're fixing bugs, adding new features, improving documentation, or suggesting new ideas, your help is greatly appreciated! Just make sure you follow these simple guidelines before opening up a PR:
- Follow the [Code of Conduct](CODE_OF_CONDUCT.md): Always adhere to the Code of Conduct and be respectful of others in the community.
- Test Your Changes: Ensure your code is tested and as bug-free as possible.
- Update Documentation: If you're adding new features or making changes that require it, update the documentation accordingly.

