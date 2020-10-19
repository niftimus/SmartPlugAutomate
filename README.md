# Installing on Linux

## Pre-requisites

### Get software
- Ubuntu 20.04 (64-bit): https://ubuntu.com/download/desktop
- Anaconda: https://www.anaconda.com/products/individual

### Create a new python environment

`conda create -n SmartPlugAutomate python=3.8`

### Activate the environment

`conda activate SmartPlugAutomate`

### Clone the environment (replace home directory)

`cd /home/david`

`git clone https://github.com/niftimus/SmartPlugAutomate.git`

### Install libraries
`cd /home/david/SmartPlugAutomate`

`pip install -r requirements.txt`

## Configuration

### Edit configuration

Edit the file config/smartplug-car.json
- Ensure _plug_address_ points to the IP of the TP-Link smartplug (e.g. 10.1.2.13)
- Ensure _solar_monitor_url_ points to the URL of the Enphase monitor endpoint (e.g. http://10.1.2.3/production.json)
- Set _min_power_ is set to the expected energy consumption of the connected device
- Set _min_off_ to the minimum number of seconds to remain off (grace period)
- Set _min_on_ to the minimum number of seconds to remain on (grace period)
- Set _check_interval_ to the number of seconds for each check interval
- Set _web_port_ to the port number of the UI interface

### Create service
Create a file as root /etc/systemd/system/smartplug-car.service (replace home directory as required):
```
[Unit]
Description=SmartPlug charger (car) service

[Service]
User=david

# The configuration file application.properties should be here:
#change this to your workspace
WorkingDirectory=/home/david/SmartPlugAutomate

#path to executable. 
#executable is a bash script which calls jar file

ExecStart=/home/david/SmartPlugAutomate/go.sh --config config/smartplug-car.json
SuccessExitStatus=143
TimeoutStopSec=10
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Set the service to run automatically on startup:

`sudo systemctl enable smartplug-car.service`

## Running

Start the service:

`sudo service smartplug-car start`

Check that the service is running:

`sudo service smartplug-car status`

```
 smartplug-car.service - Smartplug charger (car) service
   Loaded: loaded (/etc/systemd/system/smartplug-car.service; enabled; vendor preset: enabled)
   Active: active (running) since Thu 2020-09-24 20:44:39 AEST; 3 weeks 3 days ago
 Main PID: 935 (go.sh)
    Tasks: 3 (limit: 4573)
   CGroup: /system.slice/smartplug-car.service
           ├─ 935 /bin/bash /home/david/SmartPlugAutomate/go.sh --config config/smartplug-car.jso
           └─1235 python smartcontrol.py --config config/smartplug-car.json
```

## Usage

Log in to the web UI:

`http://0.0.0.0:8001`

The web UI should display with the latest plug status.
Note: This UI will be available to other devices on the network. 