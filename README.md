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
We open-sourced this project on the 06/06/2024 and it is still work in progress. This means that you may find bugs, missing features, and lack of tests. We are working on improving all of this, 

### OCPP 1.6

- Core (Done)
- Firmware Management (Done)
- Local Auth List Management (Done)
- Reservation (Not Done)
- Smart Charging (Semi Done)
- Remote Trigger (Done)

### OCPP 2.0.1

- Currently under development, the OCPP 2.0.1 version is not yet fully implemented, but we're working on it.

### How to run
We suggest to build and run this project using docker, this can be done as follows:

```shell
docker-compose up --build 
```
### Interactive API docs
You will see the automatic interactive API documentation:
- Public API: (http://127.0.0.1:8000/docs)
- Private API: (http://127.0.0.1:8800/docs)

### Get started guides
- To access the interactive docs for the
- Fo

### Known issues
- Need to add tests

### How to contribute

We welcome contributions from everyone who is willing to improve this project. Whether you're fixing bugs, adding new features, improving documentation, or suggesting new ideas, your help is greatly appreciated! Just make sure you follow these simple guidelines before opening up a PR:

    Follow the Code of Conduct: Always adhere to the Code of Conduct and be respectful of others in the community.
    Test Your Changes: Ensure your code is tested and as bug-free as possible.
    Update Documentation: If you're adding new features or making changes that require it, update the documentation accordingly.

