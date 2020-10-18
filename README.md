# Installing on Linux

##Pre-requisites
- Ubuntu 20.04 (64-bit): https://ubuntu.com/download/desktop
- Anaconda: https://www.anaconda.com/products/individual

##Clone the environment (replace home directory)
`cd /home/david`
`git clone https://github.com/niftimus/SmartPlugAutomate.git`

##Create a new python environment
`conda create -n SmartPlugAutomate python=3.8`

##Activate the environment
`conda activate SmartPlugAutomate`

##Install libraries
`pip install -r requirements.txt`

##Edit configuration

Edit the file config/smartplug-car.json
- Ensure plug_address points to the IP of the TP-Link smartplug
- Ensure min_power is set to the expected energy consumption of the plug
- Ensure solar_monitor_url points to the URL of the Enphase monitor endpoint

##Create service
Create a file /etc/systemd/system/smartplug-car.service:
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

Set the service to run automatically:

`sudo systemctl enable smartplug-car.service`

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
 ...
```

##Log in to the web UI
Open the following in a new browser:

`http://0.0.0.0:8001`