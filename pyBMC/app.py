
import os

from flask import Flask, request
from . import Sensors, logger

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

    @app.route("/api/v1/state")
    def get_state():
        sensors.update_state()
        data = { }

        fans = []
        for fan in sensors.fans:
            fans.append({
                "name": fan.name,
                "rpm": fan.rpm,
                "duty_cycle": fan.duty_cycle
            })

        data.update({
            "fans": fans,
            "tempSensor": {
                "temperature_c": sensors.temp.temperature_c,
                "temperature_f": sensors.temp.temperature_f,
                "humidity": sensors.temp.humidity
            },
            "psu": {
                "ps_ok": sensors.psu.ps_ok.state
            }
        })
        return data

    @app.route("/api/v1/fan/<int:fan_id>", methods=["GET", "PUT"])
    def fan_state(fan_id):
        if fan_id < 0 or fan_id >= len(sensors.fans):
            return "Fan not found", 404

        fan = sensors.fans[fan_id]
        if request.method == "GET":
            return {
                "name": fan.name,
                "rpm": fan.rpm,
                "duty_cycle": fan.duty_cycle
            }
        elif request.method == "PUT":
            new_duty_cycle = int(request.form["duty_cycle"])
            if new_duty_cycle < 0 or new_duty_cycle > 100:
                return "Invalid duty cycle", 400

            fan.set_speed(new_duty_cycle)
            return "", 204


    @app.route("/api/v1/psu/power_state", methods=["GET", "PUT"])
    def power_switch():
        if request.method == "GET":
            return {
                "psu": {
                    "power_state": sensors.psu.ps_ok.state
                }
            }
        else:
            new_state = request.form["power_state"]
            #return f"power_switch[put]: new_state = {new_state}"
            sensors.psu.power_switch.write(new_state)


    return app
