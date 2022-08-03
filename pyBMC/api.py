
from quart import Blueprint, request, websocket
import asyncio
import json
from . import Sensors, rpi

sensors = Sensors.Sensors()

bp = Blueprint("api", __name__, url_prefix="/api/v1")

def build_fan(index):
    fan = sensors.case_fans[index]
    return {
        "id": fan.id,
        "name": fan.name,
        "rpm": fan.rpm,
        "dutyCycle": fan.duty_cycle
    }

def build_temp(index):
    temp = sensors.temp
    return {
        "id": index,
        "name": temp.name,
        "temperatureC": temp.temperature_c,
        "humidity": temp.humidity
    }

def build_psu():
    return {
        "powerState": sensors.psu.power_switch,
        "powerOk": sensors.psu.power_ok,
    }

@bp.route("/bmc/info")
async def bmc_info():
    return rpi.get_system_info()

@bp.route("/bmc/stats")
async def bmc_stats():
    return rpi.get_system_stats()

@bp.route("/state")
async def get_state():
    sensors.update_state()
    data = { }

    fan_data = []
    for i in range(len(sensors.case_fans)):
        fan_data.append(build_fan(i))

    data.update({
        "fans": fan_data,
        "tempSensor": build_temp(0),
        "psu": build_psu()
    })
    return data

@bp.route("/fan/<int:fan_id>", methods=["GET", "PATCH"])
async def fan_state(fan_id):
    if fan_id < 0 or fan_id >= len(sensors.fans):
        return "Fan not found", 404

    if request.method == "GET":
        return build_fan(fan_id)

    elif request.method == "PATCH":
        data = request.get_json()
        new_duty_cycle = data["dutyCycle"]
        if new_duty_cycle < 0 or new_duty_cycle > 100:
            return "Invalid duty cycle", 400

        fan = sensors.fans[fan_id]
        fan.set_speed(new_duty_cycle)
        return "", 204

@bp.route("/temp/<int:temp_id>")
async def temp_state(temp_id):
    # We only support one for now
    if temp_id != 0:
        return "Temp sensor not found", 404

    return {
        "tempSensor": build_temp(0)
    }

@bp.route("/psu", methods=["GET", "PATCH"])
async def psu_state():
    if request.method == "GET":
        return build_psu()

    elif request.method == "PATCH":
        data = request.get_json()
        new_state = data["powerState"]
        valid_on_values = [1, True, "on"]
        valid_off_values = [0, False, "off"]
        if new_state not in valid_on_values and new_state not in valid_off_values:
            return "Invalid power state", 400

        # Convert to boolean
        new_state = (new_state in valid_on_values)
        sensors.psu.power_switch.write(new_state)

#
# Websocket support
#

async def websocket_send(data):
    try:
        while True:
            await websocket.send(data)
    except asyncio.CancelledError:
        # Handle disconnection here
        raise

async def dispatch_websocket_request(req):
    if "command" not in req or not req["command"]:
        raise RuntimeError("Invalid websocket request")

    cmd = req["command"]
    command_map = {
        "getBmcInfo": bmc_info,
        "getBmcStats": bmc_stats,
        "getSystemState": get_state,
    }

    callback = command_map.get(cmd)
    response_data = await callback()
    return {
        "request": cmd,
        "response": response_data
    }

async def websocket_receive():
    try:
        while True:
            data = await websocket.receive()
            request_data = json.loads(data)
            response_data = dispatch_websocket_request(request_data)
            await websocket.send(json.dumps(response_data))
    except asyncio.CancelledError:
        # Handle disconnection here
        raise

@bp.websocket("/ws")
async def handle_websocket():
    try:
        while True:
            data = await websocket.receive()
            request_data = json.loads(data)
            response_data = await dispatch_websocket_request(request_data)
            await websocket.send(json.dumps(response_data))
    except asyncio.CancelledError:
        # Handle disconnection here
        raise

# @bp.websocket("/ws")
# async def handle_websocket():
#     try:
#         producer = asyncio.create_task(websocket_send())
#         consumer = asyncio.create_task(websocket_receive())
#         await asyncio.gather(producer, consumer)
#     except asyncio.CancelledError:
#         # Handle disconnection here
#         raise
