"""Perform smart energy control based on TP Link Smart Plug"""
import asyncio
import time
import asyncclick as click
from kasa import SmartPlug, SmartDeviceException
from datetime import datetime
import requests
import json
from flask import Flask, render_template, request
import threading
import atexit

click.anyio_backend = "asyncio"
LARGE_NUMBER = 9999
POOL_TIME = 300 #Seconds

# variables that are accessible from anywhere
commonDataStruct = {}
# lock to control access to variable
dataLock = threading.Lock()
# thread handler
yourThread = threading.Thread()

class SmartControl:
    plug_address = ""
    check_interval = 0
    overall_net = 0
    switch_count = 0
    plug_consumption = 0
    is_on = None
    overall_production = 0
    overall_consumption = 0
    min_on = LARGE_NUMBER
    min_off = LARGE_NUMBER
    min_power = LARGE_NUMBER
    is_smartcontrol_enabled = True
    current_time = 0
    message = ""
    default_min_power = LARGE_NUMBER
    default_min_off = LARGE_NUMBER
    default_min_on = LARGE_NUMBER

gv_smartcontrol = SmartControl()

def CommandWithConfigFile(config_file_param_name):
    class CustomCommandClass(click.Command):
        def invoke(self, ctx):
            config_file = ctx.params[config_file_param_name]
            if config_file is not None:
                with open(config_file) as f:
                    config_data = json.load(f)
                    for param, value in ctx.params.items():
                        if param in config_data:
                            ctx.params[param] = config_data[param]
            return super(CustomCommandClass, self).invoke(ctx)

    return CustomCommandClass

@click.command(cls=CommandWithConfigFile('config'),context_settings=dict(ignore_unknown_options=True,allow_extra_args=True))
@click.option('--plug_address', default="10.1.2.12", help='IP address of Smart Plug device.', type=str, required=True)
@click.option('--solar_monitor_url', default="http://10.1.2.3/production.json", help='URL of Solar Monitor device.',
              type=str, required=True)
@click.option('--min_power', default=1700, help='Minimum solar power in Watts before switching on.', type=int,
              required=True)
@click.option('--min_off', default=60, help='Minimum off period in seconds.', type=int, required=True)
@click.option('--min_on', default=60, help='Minimum on period in seconds.', type=int, required=True)
@click.option('--check_interval', default=5, help='Check interval in seconds.', type=int, required=True)
@click.option('--config', type=click.Path(), help='Path to config file name (optional).', required=False)
@click.pass_context
async def main(ctx, config, plug_address, solar_monitor_url, check_interval, min_power, min_off, min_on):
    """Main control loop"""
    global gv_smartcontrol

    gv_smartcontrol.plug_address= plug_address
    gv_smartcontrol.check_interval=check_interval
    gv_smartcontrol.min_power=min_power
    gv_smartcontrol.min_on = min_on
    gv_smartcontrol.min_off = min_off
    gv_smartcontrol.switch_count = 0
    gv_smartcontrol.default_min_power = min_power
    gv_smartcontrol.default_min_off = min_off
    gv_smartcontrol.default_min_on = min_on

    plug = SmartPlug(plug_address)
    last_ontime = time.time()
    last_offtime = last_ontime

    while True:
        try:
            action_string = ""
            gv_smartcontrol.current_time = time.time()
            await plug.update()
            plugRealtime = await plug.get_emeter_realtime()
            gv_smartcontrol.is_on = plug.is_on
            r = requests.get(solar_monitor_url, timeout=3)
            solar_json = r.json()
            gv_smartcontrol.overall_production = (solar_json["production"][1]["wNow"])
            gv_smartcontrol.overall_consumption = (solar_json["consumption"][0]["wNow"])
            gv_smartcontrol.overall_net = gv_smartcontrol.overall_production - gv_smartcontrol.overall_consumption
            gv_smartcontrol.plug_consumption = plugRealtime["power_mw"] / 1000

            time_since_off = gv_smartcontrol.current_time - last_offtime
            time_since_on = gv_smartcontrol.current_time - last_ontime

            if (gv_smartcontrol.is_smartcontrol_enabled):
                if (gv_smartcontrol.is_on):
                    if ((gv_smartcontrol.overall_net + gv_smartcontrol.plug_consumption) >= gv_smartcontrol.min_power):
                        threshold_string = "Overall is above minimum."
                        action_string = "Leaving on."
                    else:
                        threshold_string = "Overall is under minimum."
                        if (time_since_on < gv_smartcontrol.min_on):
                            action_string = "Leaving on."
                        else:
                            action_string = "Turning off."
                            await plug.turn_off()
                            last_offtime = gv_smartcontrol.current_time
                            gv_smartcontrol.switch_count += 1
                else:
                    if ((gv_smartcontrol.overall_net + gv_smartcontrol.plug_consumption) >= gv_smartcontrol.min_power):
                        threshold_string = "Overall is above minimum."
                        if (time_since_off < gv_smartcontrol.min_off):
                            action_string = "Leaving off."
                        else:
                            action_string = "Turning on."
                            last_ontime = gv_smartcontrol.current_time
                            await plug.turn_on()
                            gv_smartcontrol.switch_count += 1
                    else:
                        threshold_string = "Overall is under minimum."
                        action_string = "Leaving off."
            else:
                threshold_string = "Smart control disabled."
                if (gv_smartcontrol.is_on):
                    action_string = "Leaving on."
                else:
                    action_string = "Leaving Off."

            gv_smartcontrol.message = f'{threshold_string} {action_string}'
            print(
                f'[{int(gv_smartcontrol.current_time)}] {gv_smartcontrol.is_smartcontrol_enabled}, Overall W: {int(gv_smartcontrol.overall_net):5},Min power W:{int(gv_smartcontrol.min_power):5}, Plug W: {int(gv_smartcontrol.plug_consumption):5}, Secs since on: {int(time_since_on):5}, Secs since off: {int(time_since_off):5}, Switch count: {gv_smartcontrol.switch_count:5}, Plug on?: {gv_smartcontrol.is_on:5} ==> {threshold_string} {action_string}')
        except SmartDeviceException as ex:
            print(f'[{int(gv_smartcontrol.current_time)}] Plug communication error ({ex}). Has it been disconnected?')
        except requests.exceptions.Timeout:
            print('HTTP Timeout exception... will retry next cycle.')
        except requests.exceptions.ConnectionError:
            print('HTTP Connection Error... will retry next cycle.')
        time.sleep(gv_smartcontrol.check_interval - (time.time() % gv_smartcontrol.check_interval))

def run_main(loop):
    asyncio.set_event_loop(loop)
    #loop.run_until_complete(main())
    main()

def create_app():
    app = Flask(__name__)

    def interrupt():
        global yourThread
        yourThread.cancel()

    def doStuff():
        global commonDataStruct
        global yourThread
        # with dataLock:
        # Do your stuff with commonDataStruct Here

        # Set the next thread to happen
        #yourThread = threading.Thread(target=main)
        loop = asyncio.new_event_loop()
        yourThread = threading.Thread(target=run_main, args=(loop,))
        yourThread.start()
        #asyncio.run(main2())

    def doStuffStart():
        # Do initialisation stuff here
        global yourThread
        # Create your thread
        #yourThread = threading.Thread(target=main)
        loop = asyncio.new_event_loop()
        yourThread = threading.Thread(target=run_main, args=(loop,))
        yourThread.start()
        #asyncio.run(main2())

    # Initiate
    doStuffStart()

    # When you kill Flask (SIGTERM), clear the trigger for the next thread
    atexit.register(interrupt)
    return app

app = create_app()

@app.template_filter('ctime')
def timectime(s):
    return datetime.fromtimestamp(s).strftime('%Y-%m-%d %H:%M:%S') # datetime.datetime.fromtimestamp(s)

@app.route('/', methods=['GET','POST'])
def webInterface():
    error = None
    global gv_smartcontrol
    if request.method == 'POST':
        gv_smartcontrol.min_power = int(request.form['newMinPower'])
        gv_smartcontrol.min_on = int(request.form['newMinOn'])
        gv_smartcontrol.min_off = int(request.form['newMinOff'])
        if (request.form['is_smartcontrolEnabled'] == 'on'):
            gv_smartcontrol.is_smartcontrol_enabled = True
        else:
            gv_smartcontrol.is_smartcontrol_enabled = False
    return render_template('smartcontrol.html', smartcontrol=gv_smartcontrol)

@click.command(cls=CommandWithConfigFile('config'),context_settings=dict(ignore_unknown_options=True,allow_extra_args=True))
@click.option('--web_host', default="0.0.0.0", help='Host IP for web interface', type=str, required=True)
@click.option('--web_port', default="5000", help='Port for web interface', type=str, required=True)
@click.option('--config', type=click.Path(), help='Path to config file name (optional).', required=False)
def cli(web_host, web_port, config):
    app.run(host=web_host, port = web_port)

if __name__ == "__main__":
    cli()



