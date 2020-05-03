"""Perform smart energy control based on TP Link Smart Plug"""
import asyncio
import time
import asyncclick as click
from kasa import SmartPlug

click.anyio_backend = "asyncio"

@click.command()
@click.option('--plug_address', default="10.1.2.12", help='IP address of Smart Plug device.')
@click.option('--solar_monitor_address', default="10.1.2.3", help='IP address of Solar Monitor device.')
@click.option('--check_interval', default=1, help='Check interval in seconds.')
@click.option('--min_power', default=400, help='Minimum solar power in Watts.')
@click.option('--min_off', default=300, help='Minimum off period in seconds.')
@click.option('--min_on', default=60, help='Minimum on period in seconds.')
@click.pass_context
async def main(ctx, address,period):
    """Main monitoring loop"""
    plug = SmartPlug(address)
    while True:
        await plug.update()
        plugStatus = await plug.get_emeter_realtime()
        print(plugStatus)
        time.sleep(period - (time.time() % period))

if __name__ == "__main__":
    main()