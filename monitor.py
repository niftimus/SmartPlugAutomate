"""Monitor TP link smart plug energy consumption and print output in CSV format"""
import asyncio
import time
import asyncclick as click
from kasa import SmartPlug, SmartDeviceException
from flask import Flask, render_template
import threading

app = Flask(__name__)
click.anyio_backend = "asyncio"
gv_myplugstatus = {}
gv_plug_address = ""
gv_monitoring_period = 0

async def getReading(plug):
    """Get updated reading"""
    try:
        await plug.update()
        plugStatus = await plug.get_emeter_realtime()
        currentTime = int(time.time())
        global gv_myplugstatus
        gv_myplugstatus["timestamp"] = currentTime
        gv_myplugstatus["voltage"] = plugStatus["voltage_mv"]/1000
        gv_myplugstatus["current"] = plugStatus["current_ma"]/1000
        gv_myplugstatus["power"] = plugStatus["power_mw"]/1000000
        gv_myplugstatus["energy"] = plugStatus["total_wh"]/1000
        return(f'{gv_myplugstatus["timestamp"]},{gv_myplugstatus["voltage"]},{gv_myplugstatus["current"]},{gv_myplugstatus["power"]},{gv_myplugstatus["energy"]}')
    except SmartDeviceException as ex:
        currentTime = int(time.time())
        return (f'{currentTime}, Plug communication error ({ex}). Has it been disconnected?')

@click.command()
@click.option('--address', default="10.1.2.12", help='IP address of device.')
@click.option('--period', default=1, help='Monitoring period in seconds.')
@click.pass_context
async def main(ctx, address,period):
    """Main monitoring loop"""
    global gv_plug_address, gv_monitoring_period
    gv_plug_address=address
    gv_monitoring_period=period
    plug = SmartPlug(address)
    print(
        f'"Timestamp","Voltage (V)", "Current (A)", "Power (kW)", "Energy (kWh)"')
    while True:
        reading = await getReading(plug)
        print(reading)
        time.sleep(period - (time.time() % period))

@app.route('/')
def monitor():
    return render_template('monitor.html', plug_address=gv_plug_address, monitoring_period=gv_monitoring_period, plugstatus=gv_myplugstatus)

if __name__ == "__main__":
    threading.Thread(target=app.run).start()
    main()
