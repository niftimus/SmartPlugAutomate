"""Perform smart energy control based on TP Link Smart Plug"""
import asyncio
import time
import asyncclick as click
from kasa import SmartPlug, SmartDeviceException
import requests
import json

click.anyio_backend = "asyncio"

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
@click.option('--plug_address', default="10.1.2.12", help='IP address of Smart Plug device.', type=str,required=True)
@click.option('--solar_monitor_url', default="http://10.1.2.3/production.json", help='URL of Solar Monitor device.', type=str, required=True)
@click.option('--min_power', default=1700, help='Minimum solar power in Watts before switching on.',type=int, required=True)
@click.option('--min_off', default=60, help='Minimum off period in seconds.', type=int,required=True)
@click.option('--min_on', default=60, help='Minimum on period in seconds.', type=int,required=True)
@click.option('--check_interval', default=5, help='Check interval in seconds.',type=int, required=True)
@click.option('--config', type=click.Path(),help='Path to config file name (optional).',required=False)
@click.pass_context
async def main(ctx, config, plug_address, solar_monitor_url, check_interval, min_power, min_off, min_on):
    """Main monitoring loop"""
    plug = SmartPlug(plug_address)
    last_ontime = time.time()
    last_offtime = last_ontime
    switchcount = 0
    while True:
        try:
            action_string = ""
            current_time = time.time()
            await plug.update()
            plugRealtime = await plug.get_emeter_realtime()
            is_on = plug.is_on
            r = requests.get(solar_monitor_url)
            solar_json = r.json()
            overall_production = (solar_json["production"][1]["wNow"])
            overall_consumption = (solar_json["consumption"][0]["wNow"])
            overall_net = overall_production - overall_consumption
            plug_consumption = plugRealtime["power_mw"]/1000

            time_since_off = current_time - last_offtime
            time_since_on = current_time - last_ontime

            if(is_on):
                if((overall_net + plug_consumption)>=min_power):
                    threshold_string = "Overall is above minimum."
                    action_string = "Leaving on."
                else:
                    threshold_string = "Overall is under minimum."
                    if (time_since_on<min_on):
                        action_string = "Leaving on."
                    else:
                        action_string = "Turning off."
                        await plug.turn_off()
                        last_offtime = current_time
                        switchcount += 1
            else:
                if((overall_net + plug_consumption)>=min_power):
                    threshold_string = "Overall is above minimum."
                    if (time_since_off<min_off):
                        action_string = "Leaving off."
                    else:
                        action_string = "Turning on."
                        last_ontime = current_time
                        await plug.turn_on()
                        switchcount+=1
                else:
                    threshold_string = "Overall is under minimum."
                    action_string = "Leaving off."

            print(f'[{int(current_time)}] Overall W: {int(overall_net):5}, Plug W: {int(plug_consumption):5}, Secs since on: {int(time_since_on):5}, Secs since off: {int(time_since_off):5}, Switch count: {switchcount:5}, Plug on?: {is_on:5} ==> {threshold_string} {action_string}')
        except SmartDeviceException as ex:
            print(f'[{int(current_time)}] Plug communication error ({ex}). Has it been disconnected?')
        time.sleep(check_interval - (time.time() % check_interval))

if __name__ == "__main__":
    main()