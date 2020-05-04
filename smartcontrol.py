"""Perform smart energy control based on TP Link Smart Plug"""
import asyncio
import time
import asyncclick as click
from kasa import SmartPlug
import requests
import json

click.anyio_backend = "asyncio"

@click.command()
@click.option('--plug_address', default="10.1.2.12", help='IP address of Smart Plug device.')
@click.option('--solar_monitor_url', default="http://10.1.2.3/production.json", help='IP address of Solar Monitor device.')
@click.option('--check_interval', default=5, help='Check interval in seconds.')
@click.option('--min_power', default=1700, help='Minimum solar power in Watts before switching on.')
@click.option('--min_off', default=60, help='Minimum off period in seconds.')
@click.option('--min_on', default=60, help='Minimum on period in seconds.')
@click.pass_context
async def main(ctx, plug_address, solar_monitor_url, check_interval, min_power, min_off, min_on):
    """Main monitoring loop"""
    plug = SmartPlug(plug_address)
    last_ontime = time.time()
    last_offtime = last_ontime
    switchcount = 0
    while True:
        action_string = ""
        await plug.update()
        plugRealtime = await plug.get_emeter_realtime()
        is_on = plug.is_on
        r = requests.get(solar_monitor_url)
        solar_json = r.json()
        current_time = time.time()
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
        time.sleep(check_interval - (time.time() % check_interval))

if __name__ == "__main__":
    main()