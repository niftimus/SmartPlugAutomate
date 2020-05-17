"""Perform smart energy control based on TP Link Smart Plug"""
import asyncio
import time
import asyncclick as click
from kasa import SmartPlug, SmartDeviceException
import requests
import json
from flask import Flask, render_template
import threading

app = Flask(__name__)
click.anyio_backend = "asyncio"
gv_plug_address = ""
gv_monitoring_period = 0
gv_overall_net = 0
gv_switchcount = 0
gv_plug_consumption = 0
gv_is_on = None
gv_overall_production = 0
gv_overall_consumption = 0
gv_min_on = 0
gv_min_off = 0


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
@click.pass_context
async def main(ctx, config, plug_address, solar_monitor_url, check_interval, min_power, min_off, min_on):
    """Main monitoring loop"""
    plug = SmartPlug(plug_address)
    last_ontime = time.time()
    last_offtime = last_ontime
    global gv_plug_address, gv_check_interval, gv_overall_net, gv_switchcount, gv_is_on, gv_overall_production, gv_overall_consumption, gv_current_time, gv_min_off, gv_min_on, gv_min_power
    gv_min_off= min_off
    gv_min_on = min_on
    gv_switchcount = 0
    gv_plug_address = plug_address
    gv_check_interval = check_interval
    gv_min_power = min_power
    while True:
        try:
            action_string = ""
            gv_current_time = time.time()
            await plug.update()
            plugRealtime = await plug.get_emeter_realtime()
            gv_is_on = plug.is_on
            r = requests.get(solar_monitor_url)
            solar_json = r.json()
            gv_overall_production = (solar_json["production"][1]["wNow"])
            gv_overall_consumption = (solar_json["consumption"][0]["wNow"])
            gv_overall_net = gv_overall_production - gv_overall_consumption
            gv_plug_consumption = plugRealtime["power_mw"] / 1000

            time_since_off = gv_current_time - last_offtime
            time_since_on = gv_current_time - last_ontime

            if (gv_is_on):
                if ((gv_overall_net + gv_plug_consumption) >= min_power):
                    threshold_string = "Overall is above minimum."
                    action_string = "Leaving on."
                else:
                    threshold_string = "Overall is under minimum."
                    if (time_since_on < min_on):
                        action_string = "Leaving on."
                    else:
                        action_string = "Turning off."
                        await plug.turn_off()
                        last_offtime = gv_current_time
                        gv_switchcount += 1
            else:
                if ((gv_overall_net + gv_plug_consumption) >= min_power):
                    threshold_string = "Overall is above minimum."
                    if (time_since_off < min_off):
                        action_string = "Leaving off."
                    else:
                        action_string = "Turning on."
                        last_ontime = gv_current_time
                        await plug.turn_on()
                        gv_switchcount += 1
                else:
                    threshold_string = "Overall is under minimum."
                    action_string = "Leaving off."

            print(
                f'[{int(gv_current_time)}] Overall W: {int(gv_overall_net):5}, Plug W: {int(gv_plug_consumption):5}, Secs since on: {int(time_since_on):5}, Secs since off: {int(time_since_off):5}, Switch count: {gv_switchcount:5}, Plug on?: {gv_is_on:5} ==> {threshold_string} {action_string}')
        except SmartDeviceException as ex:
            print(f'[{int(gv_current_time)}] Plug communication error ({ex}). Has it been disconnected?')
        time.sleep(check_interval - (time.time() % check_interval))


@app.route('/')
def monitor():
    return render_template('smartcontrol.html', plug_address=gv_plug_address, check_interval=gv_check_interval,
                           timestamp=gv_current_time, overall_net=gv_overall_net, plug_consumption=gv_plug_consumption,
                           is_on=gv_is_on, min_on = gv_min_on, min_off = gv_min_off, min_power=gv_min_power)

if __name__ == "__main__":
    threading.Thread(target=app.run).start()
    main()
