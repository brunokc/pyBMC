#!/usr/bin/env python
#
# pyBMC
#
# Based on the work of DriftKingTW
# (https://blog.driftking.tw/en/2019/11/Using-Raspberry-Pi-to-Control-a-PWM-Fan-and-Monitor-its-Speed/)
#

import pigpio
import yaml
from . import DHT22, logger

CONFIG_FILE = "pybmc.conf"
HARDWARE_CONFIG_FILE = "pybmc.hardware.conf"

class RpmPin:
    def __init__(self, pi, pin, weighting=0.0, pulses_per_rev=1) -> None:
        self._pi = pi
        self._pin = pin
        self._pulses_per_rev = pulses_per_rev
        self._high_tick = None
        self._period = None

        # Watchdog: 200ms
        self._watchdog = 200

        # Weighting is a number between 0 and 1 and indicates how much the old reading affects the
        # new reading. It defaults to 0 which means the old reading has no effect. This may be used
        # to smooth the data.
        if weighting < 0.0:
            weighting = 0.0
        elif weighting > 0.99:
            weighting = 0.99

        self._old_value_weight = weighting
        self._new_value_weight = 1.0 - weighting

        self._pi.set_mode(self._pin, pigpio.INPUT)
        self._pi.set_pull_up_down(self._pin, pigpio.PUD_UP)
        self._callback = self._pi.callback(self._pin, pigpio.FALLING_EDGE, self.on_rpm_pin_falling_edge)
        self._pi.set_watchdog(self._pin, self._watchdog)

    def on_rpm_pin_falling_edge(self, pin, level, tick):
        if level == 0: # Falling edge
            if self._high_tick is not None:
                t = pigpio.tickDiff(self._high_tick, tick)
                if self._period is not None:
                    self._period = (self._period * self._old_value_weight) + (t * self._new_value_weight)
                else:
                    self._period = t
            self._high_tick = tick

        elif level == 2: # Watchdog timeout
            if self._period is not None:
                if self._period < 2000000000:
                    self._period += (self._watchdog * 1000)

    def stop(self):
        self._pi.set_watchdog(self._pin, 0)
        self._callback.cancel()
        self._callback = None

    def reset(self):
        self._high_tick = None
        self._period = None

    @property
    def rpm(self):
        rpm = 0.0
        if self._period is not None:
            rpm = 60000000.0 / (self._period * self._pulses_per_rev)
        return rpm


class PwmPin:
    def __init__(self, pi, pin, pwm_frequency) -> None:
        self._pi = pi
        self._pin = pin
        self._duty_cycle = 100

        self._pi.set_mode(self._pin, pigpio.OUTPUT)
        self._pi.set_PWM_frequency(self._pin, pwm_frequency)
        self._pi.set_PWM_range(self._pin, 100)
        self._pi.set_PWM_dutycycle(self._pin, self._duty_cycle)

    def stop(self):
        self.set_duty_cycle(0)

    @property
    def duty_cycle(self):
        return self._duty_cycle

    def set_duty_cycle(self, value):
        self._pi.set_PWM_dutycycle(self._pin, value)
        self._duty_cycle = value


class Fan:
    def __init__(self, id, name, pi, rpm_pin, pwm_pin, pwm_frequency, weighting=0.0, pulses_per_rev=1) -> None:
        self.id = id
        self.name = name

        logger.log(f"Setting up GPIOs for fan {self.name}...")
        logger.log(f"   RPM pin: {rpm_pin}")
        self.rpm_pin = RpmPin(pi, rpm_pin, weighting, pulses_per_rev)

        logger.log(f"   PWM pin: {pwm_pin}")
        self.pwm_pin = PwmPin(pi, pwm_pin, pwm_frequency)

    def stop(self):
        self.rpm_pin.stop()
        self.pwm_pin.stop()

    def reset(self):
        self.rpm_pin.reset()

    @property
    def rpm(self):
        return self.rpm_pin.rpm

    @property
    def duty_cycle(self):
        return self.pwm_pin.duty_cycle

    def set_speed(self, speed):
        self.pwm_pin.set_duty_cycle(speed)


class TempHumiditySensor:
    def __init__(self, name, pi, pin) -> None:
        self.name = name
        self._pin = pin
        self._temp_c = 0
        self._humidity = 0

        logger.log(f"Setting up GPIOs for temp sensor {self.name}...")
        self._device = DHT22.sensor(pi, pin)

    def update_state(self):
        self._device.update_state()
        try:
            temp_c = self._device.temperature()
            humidity = self._device.humidity()

            if temp_c is not None and humidity is not None :
                self._temp_c = temp_c
                self._humidity = humidity
        except RuntimeError:
            pass

    def stop(self):
        self._device.cancel()

    @property
    def temperature_c(self):
        return self._temp_c

    @property
    def humidity(self):
        return self._humidity


class PsuPin:
    def __init__(self, name, pi, pin, mode) -> None:
        self._name = name
        self._pi = pi
        self._pin = pin
        self._mode = mode
        self._state = 0

        if self._mode == pigpio.INPUT:
            self._pi.set_mode(self._pin, pigpio.INPUT)
            self._pi.set_pull_up_down(self._pin, pigpio.PUD_DOWN)
        else:
            self._pi.set_mode(self._pin, pigpio.OUTPUT)
            self._pi.write(self._pin, 0)

    def update_state(self):
        self._state = self._pi.read(self._pin)

    def stop(self):
        pass

    @property
    def state(self):
        return self._state

    def read(self):
        if self._mode == pigpio.OUTPUT:
            raise RuntimeError("read is invalid on an output pin")
        return self._state

    def write(self, value):
        if self._mode == pigpio.INPUT:
            raise RuntimeError("write is invalid on an input pin")

        self._pi.write(self._pin, value)
        self._state = value

    def toggle(self):
        if self._mode == pigpio.INPUT:
            raise RuntimeError("toggle is invalid on an input pin")

        new_state = not self._state
        self.write(new_state)


class Psu:
    def __init__(self, pi, power_switch_pin, power_ok_pin) -> None:
        self._power_switch = PsuPin("ps_switch", pi, power_switch_pin, pigpio.OUTPUT)
        self._power_ok = PsuPin("ps_ok", pi, power_ok_pin, pigpio.INPUT)

    def update_state(self):
        self._power_switch.update_state()
        self._power_ok.update_state()

    def stop(self):
        self._power_switch.stop()
        self._power_ok.stop()

    @property
    def power_switch(self):
        return self._power_switch

    @property
    def power_ok(self):
        return self._power_ok


def load_config(file_path):
    with open(file_path, "r") as config_file:
        return yaml.safe_load(config_file)


class Sensors:
    def __init__(self) -> None:
        self._pi = pigpio.pi()

        hwconfig = load_config(HARDWARE_CONFIG_FILE)
        fan_settings = hwconfig["pybmc"]["fans"]["settings"]
        pulses_per_revolution = fan_settings["pulses-per-revolution"]
        pwm_frequency = fan_settings["pwm-frequency"]
        weighting = fan_settings["weighting"]

        swconfig = load_config(CONFIG_FILE)
        fan_config = swconfig["pybmc"]["fans"]
        default_fan_speed = fan_config["default-speed"]
        self.sync_fans_speeds = fan_config["sync-speeds"]

        self.case_fans = []
        fan_id = 0
        for fan_data in hwconfig["pybmc"]["fans"]["case-fans"]:
            name = fan_data["name"]
            rpm_pin = fan_data["rpm-pin"]
            pwm_pin = fan_data["pwm-pin"]
            fan = Fan(fan_id, name, self._pi, rpm_pin, pwm_pin, weighting, pulses_per_revolution, pwm_frequency)
            fan.set_speed(default_fan_speed)
            self.case_fans.append(fan)
            fan_id += 1

        # We only support a single temp/humidity sensor for now
        temp_data = hwconfig["pybmc"]["temp-sensors"]
        name = temp_data[0]["name"]
        pin = temp_data[0]["pin"]
        self.temp = TempHumiditySensor(name, self._pi, pin)

        psu_data = hwconfig["pybmc"]["psu"]
        power_switch_pin = psu_data["power-switch-pin"]
        power_ok_pin = psu_data["power-ok-pin"]
        self.psu = Psu(self._pi, power_switch_pin, power_ok_pin)

    def stop(self):
        self.psu.stop()
        self.temp.stop()
        for fan in self.case_fans:
            fan.stop()
        self._pi.stop()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def update_state(self):
        self.temp.update_state()
        self.psu.update_state()

        # If power is not on, we need to manually reset the state of the fans
        # as we haven't had a chance to do that since the power was cut.
        # Also, if power ok is set while power switch is off, that means the
        # power was externally switched, so don't reset the fans in that case.
        if not self.psu.power_switch.state and not self.psu.power_ok.state:
            for fan in self.case_fans:
                fan.reset()
