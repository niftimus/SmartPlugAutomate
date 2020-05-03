"""Monitor TP link smart plug energy consumption and print output in CSV format"""
import asyncio
import time
import asyncclick as click
from kasa import SmartPlug

click.anyio_backend = "asyncio"

async def getReading(plug):
    """Get updated reading"""
    await plug.update()
    plugStatus = await plug.get_emeter_realtime()
    currentTime = int(time.time())
    return(f'{currentTime}, {plugStatus["voltage_mv"]/1000}, {plugStatus["current_ma"]/1000}, {plugStatus["power_mw"]/1000000}, {plugStatus["total_wh"]/1000}')

@click.command()
@click.option('--address', default="10.1.2.12", help='IP address of device.')
@click.option('--period', default=1, help='Monitoring period in seconds.')
@click.pass_context
async def main(ctx, address,period):
    """Main monitoring loop"""
    plug = SmartPlug(address)
    print(
        f'"Timestamp","Voltage (V)", "Current (A)", "Power (kW)", "Energy (kWh)"')
    while True:
        reading = await getReading(plug)
        print(reading)
        time.sleep(period - (time.time() % period))

if __name__ == "__main__":
    main()