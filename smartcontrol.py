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
@click.option('--check_interval', default=1, help='Check interval in seconds.')
@click.option('--min_power', default=400, help='Minimum solar power in Watts.')
@click.option('--min_off', default=300, help='Minimum off period in seconds.')
@click.option('--min_on', default=60, help='Minimum on period in seconds.')
@click.pass_context
async def main(ctx, plug_address, solar_monitor_url, check_interval, min_power, min_off, min_on):
    """Main monitoring loop"""
    plug = SmartPlug(plug_address)
    while True:
        await plug.update()
        plugStatus = await plug.get_emeter_realtime()
        print(plugStatus)
        time.sleep(check_interval - (time.time() % check_interval))
        r = requests.get(solar_monitor_url)
        solar_json = r.json()
        current_time = time.ctime()
        current_production = (solar_json["production"][1]["wNow"])
        current_consumption = (solar_json["consumption"][0]["wNow"])
        current_net = current_production - current_consumption


if __name__ == "__main__":
    main()