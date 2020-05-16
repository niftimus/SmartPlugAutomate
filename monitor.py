"""Monitor TP link smart plug energy consumption and print output in CSV format"""
import asyncio
import time
import asyncclick as click
from kasa import SmartPlug, SmartDeviceException
from flask import Flask
import threading

app = Flask(__name__)
click.anyio_backend = "asyncio"
msg = ""


async def getReading(plug):
    """Get updated reading"""
    try:
        await plug.update()
        plugStatus = await plug.get_emeter_realtime()
        currentTime = int(time.time())
        return(f'{currentTime}, {plugStatus["voltage_mv"]/1000}, {plugStatus["current_ma"]/1000}, {plugStatus["power_mw"]/1000000}, {plugStatus["total_wh"]/1000}')
    except SmartDeviceException as ex:
        currentTime = int(time.time())
        return (f'{currentTime}, Plug communication error ({ex}). Has it been disconnected?')

@click.command()
@click.option('--address', default="10.1.2.12", help='IP address of device.')
@click.option('--period', default=1, help='Monitoring period in seconds.')
@click.pass_context
async def main(ctx, address,period):
    """Main monitoring loop"""
    plug = SmartPlug(address)
    global msg
    print(
        f'"Timestamp","Voltage (V)", "Current (A)", "Power (kW)", "Energy (kWh)"')
    while True:
        reading = await getReading(plug)
        print(reading)

        msg=reading
        time.sleep(period - (time.time() % period))

@app.route('/')
def hello():
    return msg

if __name__ == "__main__":
    threading.Thread(target=app.run).start()
    main()
