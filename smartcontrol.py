"""Perform smart energy control based on TP Link Smart Plug"""
import asyncio
import time
import asyncclick as click
from kasa import SmartPlug, SmartDeviceException
import requests
import json
from flask import Flask, render_template, request
import threading

app = Flask(__name__)
click.anyio_backend = "asyncio"

class SmartControl:
    plug_address = ""
    check_interval = 0
    overall_net = 0
    switch_count = 0
    plug_consumption = 0
    is_on = None
    overall_production = 0
    overall_consumption = 0
    min_on = 0
    min_off = 0
    min_power = 0
    is_smartcontrol_enabled = True
    current_time = 0

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


@click.command(cls=CommandWithConfigFile('config'))
@click.option('--plug_address', default="10.1.2.12", help='IP address of Smart Plug device.', type=str, required=True)
@click.option('--solar_monitor_url', default="http://10.1.2.3/production.json", help='URL of Solar Monitor device.',
              type=str, required=True)
@click.option('--min_power', default=1700, help='Minimum solar power in Watts before switching on.', type=int,
              required=True)
@click.option('--min_off', default=60, help='Minimum off period in seconds.', type=int, required=True)
@click.option('--min_on', default=60, help='Minimum on period in seconds.', type=int, required=True)
@click.option('--check_interval', default=5, help='Check interval in seconds.', type=int, required=True)
@click.option('--config', type=click.Path(), help='Path to config file name (optional).', required=False)
@click.option('--web_port', default=5000, help='Web port.', required=True)
@click.pass_context
async def main(ctx, config, plug_address, solar_monitor_url, check_interval, min_power, min_off, min_on, web_port):
    """Main control loop"""
    threading.Thread(target=app.run(port=web_port)).start()
    global gv_smartcontrol
    gv_smartcontrol.plug_address= plug_address
    gv_smartcontrol.check_interval=check_interval
    gv_smartcontrol.min_power=min_power
    gv_smartcontrol.min_on = min_on
    gv_smartcontrol.min_off = min_off
    gv_smartcontrol.switch_count = 0

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
            r = requests.get(solar_monitor_url)
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

            print(
                f'[{int(gv_smartcontrol.current_time)}] {gv_smartcontrol.is_smartcontrol_enabled}, Overall W: {int(gv_smartcontrol.overall_net):5},Min power W:{int(gv_smartcontrol.min_power):5}, Plug W: {int(gv_smartcontrol.plug_consumption):5}, Secs since on: {int(time_since_on):5}, Secs since off: {int(time_since_off):5}, Switch count: {gv_smartcontrol.switch_count:5}, Plug on?: {gv_smartcontrol.is_on:5} ==> {threshold_string} {action_string}')
        except SmartDeviceException as ex:
            print(f'[{int(gv_current_time)}] Plug communication error ({ex}). Has it been disconnected?')
        time.sleep(gv_smartcontrol.check_interval - (time.time() % gv_smartcontrol.check_interval))


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

if __name__ == "__main__":
    main()
