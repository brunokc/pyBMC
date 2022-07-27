
import os

from flask import Flask, request, render_template
from . import Sensors
from . import version

sensors = Sensors.Sensors()

def create_app(test_config=None):
    app = Flask(__name__.split('.')[0], instance_relative_config=True)
    app.config.from_mapping(
        JSON_SORT_KEYS=False,
        # SECRET_KEY="dev",
        # DATABASE=os.path.join(app.instance_path, "pyBMC.sqlite"),
    )

    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.from_mapping(test_config)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    def build_fan(index):
        fan = sensors.fans[index]
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
            "powerState": sensors.psu.ps_ok.state
        }

    @app.route("/api/v1/state")
    def get_state():
        sensors.update_state()
        data = { }

        fan_data = []
        for i in range(len(sensors.fans)):
            fan_data.append(build_fan(i))

        data.update({
            "fans": fan_data,
            "tempSensor": build_temp(0),
            "psu": build_psu()
        })
        return data

    @app.route("/api/v1/fan/<int:fan_id>", methods=["GET", "PATCH"])
    def fan_state(fan_id):
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

    @app.route("/api/v1/temp/<int:temp_id>")
    def temp_state(temp_id):
        # We only support one for now
        if temp_id != 0:
            return "Temp sensor not found", 404

        return {
            "tempSensor": build_temp(0)
        }

    @app.route("/api/v1/psu", methods=["GET", "PATCH"])
    def psu_state():
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

    @app.route("/")
    def index():
        project_name = __name__.split('.')[0]
        project_version = version.__version__
        return render_template("main.html", **locals(), sensors = sensors)

    return app
