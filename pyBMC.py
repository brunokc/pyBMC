#!/usr/bin/env python
#
# pyBMC
#
# Based on the work of DriftKingTW
# (https://blog.driftking.tw/en/2019/11/Using-Raspberry-Pi-to-Control-a-PWM-Fan-and-Monitor-its-Speed/)
#

import sys
import time
import curses

import pigpio

import board
import adafruit_dht

# Noctua specifies 25Khz frequency for PWM control.
# For RPM reading, it says there's two pulses per rotation
# (https://noctua.at/pub/media/wysiwyg/Noctua_PWM_specifications_white_paper.pdf)
PWM_FREQUENCY = 25000
PULSES_PER_REVOLUTION = 2

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
    def __init__(self, pi, pin) -> None:
        self._pi = pi
        self._pin = pin
        self._duty_cycle = 100

        self._pi.set_mode(self._pin, pigpio.OUTPUT)
        self._pi.set_PWM_frequency(self._pin, PWM_FREQUENCY)
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
    def __init__(self, name, pi, rpm_pin, pwm_pin, weighting=0.0, pulses_per_rev=1) -> None:
        self.name = name

        log(f"Setting up GPIOs for fan {self.name}...")
        log(f"   RPM pin: {rpm_pin}")
        self.rpm_pin = RpmPin(pi, rpm_pin, weighting, pulses_per_rev)

        log(f"   PWM pin: {pwm_pin}")
        self.pwm_pin = PwmPin(pi, pwm_pin)

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
    def __init__(self, name, pin) -> None:
        self._name = name
        self._pin = pin
        self._temp_c = 0
        self._temp_f = 0
        self._humidity = 0

        log(f"Setting up GPIOs for temp sensor {self._name}...")
        self._device = adafruit_dht.DHT22(self._pin)

    def update_state(self):
        try:
            temp_c = self._device.temperature
            temp_f = 0
            if temp_c:
                temp_f = 32 + temp_c * 9 / 5
            humidity = self._device.humidity

            if temp_c is not None and temp_f is not None and humidity is not None :
                self._temp_c = temp_c
                self._temp_f = temp_f
                self._humidity = humidity
        except RuntimeError:
            pass

    def stop(self):
        if self._device:
            self._device.exit()

    @property
    def temperature_c(self):
        return self._temp_c

    @property
    def temperature_f(self):
        return self._temp_f

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
        if self._mode == pigpio.OUTPUT:
            raise RuntimeError("update_state is invalid on an output pin")

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
    def __init__(self, pi) -> None:
        self.power_switch = PsuPin("ps_switch", pi, 25, pigpio.OUTPUT)
        self.ps_ok = PsuPin("ps_ok", pi, 27, pigpio.INPUT)

    def update_state(self):
        self.ps_ok.update_state()

    def stop(self):
        self.power_switch.stop()
        self.ps_ok.stop()

class Sensors:
    def __init__(self) -> None:
        self._pi = pigpio.pi()

        self.fans = [
            Fan("fan1", self._pi, rpm_pin = 18, pwm_pin = 17, weighting=0.25, pulses_per_rev=PULSES_PER_REVOLUTION),
            Fan("fan2", self._pi, rpm_pin = 23, pwm_pin = 24, weighting=0.25, pulses_per_rev=PULSES_PER_REVOLUTION),
            Fan("fan3", self._pi, rpm_pin = 16, pwm_pin = 20, weighting=0.25, pulses_per_rev=PULSES_PER_REVOLUTION),
        ]
        self.temp = TempHumiditySensor("temp1", board.D21)
        self.psu = Psu(self._pi)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.psu.stop()
        self.temp.stop()
        for fan in self.fans:
            fan.stop()
        self._pi.stop()

    def update_state(self):
        self.temp.update_state()
        self.psu.update_state()

        # If power is not on, we need to manually reset the state of the fans
        # as we haven't had a chance to do that since the power was cut
        if not self.psu.ps_ok.state:
            for fan in self.fans:
                fan.reset()


def log(*args):
    print(*args)

def console(stdscr, sensors):
    # Hide cursor
    curses.curs_set(0)
    # Non blocking input (getch)
    stdscr.nodelay(True)

    selected_fan = 0
    sensor_update_time = 0.2
    wait_time = 0.05

    fans = sensors.fans
    temp = sensors.temp
    psu = sensors.psu

    accumulated_time = 0
    while True:
        accumulated_time += wait_time
        if accumulated_time >= sensor_update_time:
            sensors.update_state()
            accumulated_time = 0

        stdscr.addstr(0, 40, "  PyBMC v0.1  ", curses.A_REVERSE)
        stdscr.addstr(2,  9, f" Fan 1 speed: {int(fans[0].rpm)} rpm  ")
        stdscr.addstr(3,  9, f" Fan 1 PWM: {fans[0].duty_cycle}%  ", curses.A_REVERSE if selected_fan == 0 else curses.A_NORMAL)
        stdscr.addstr(2, 39, f" Fan 2 speed: {int(fans[1].rpm)} rpm  ")
        stdscr.addstr(3, 39, f" Fan 2 PWM: {fans[1].duty_cycle}%  ", curses.A_REVERSE if selected_fan == 1 else curses.A_NORMAL)
        stdscr.addstr(2, 69, f" Fan 3 speed: {int(fans[2].rpm)} rpm  ")
        stdscr.addstr(3, 69, f" Fan 3 PWM: {fans[2].duty_cycle}%  ", curses.A_REVERSE if selected_fan == 2 else curses.A_NORMAL)

        stdscr.addstr(5, 10, f"Temperature: {temp.temperature_c:.1f}C ({temp.temperature_f:.1f}F)")
        stdscr.addstr(6, 10, f"Humidity: {temp.humidity}%")

        psu_state = "on" if psu.ps_ok.state else "off"
        stdscr.addstr(8, 10, f"PSU Ok: {psu_state} ")

        stdscr.refresh()

        c = stdscr.getch()
        if c == ord('P') or c == ord('p'):
            psu.power_switch.toggle()
        elif c == curses.KEY_RIGHT:
            selected_fan = selected_fan + 1 if selected_fan < len(fans) - 1 else selected_fan
        elif c == curses.KEY_LEFT:
            selected_fan = selected_fan - 1 if selected_fan > 0 else 0
        elif c == curses.KEY_UP:
            duty_cycle = fans[selected_fan].duty_cycle
            duty_cycle = duty_cycle + 10 if duty_cycle < 100 else 100
            fans[selected_fan].set_speed(duty_cycle)
        elif c == curses.KEY_DOWN:
            duty_cycle = fans[selected_fan].duty_cycle
            duty_cycle = duty_cycle - 10 if duty_cycle > 0 else 0
            fans[selected_fan].set_speed(duty_cycle)
        elif c == ord('t') or c == ord('T'):
            pass
        elif c != curses.ERR:
            break

        time.sleep(wait_time)


def dump_data(sensors):
    fans = sensors.fans
    log(f"Fan 1: {int(fans[0].rpm)} rpm")
    log(f"Fan 2: {int(fans[1].rpm)} rpm")
    log(f"Fan 3: {int(fans[2].rpm)} rpm")

    temp = sensors.temp
    log(f"Temperature: {temp.temperature_c:.1f}C ({temp.temperature_f:.1f}F)")
    log(f"Humidity: {temp.humidity}%")

    psu_state = "on" if sensors.psu.ps_ok.state else "off"
    log(f"PSU Ok: {psu_state}")
    log()

def text_console(sensors):
    sensors.psu.power_switch.toggle()
    while True:
        sensors.update_state()
        dump_data(sensors)
        time.sleep(1)

def main():
    with Sensors() as sensors:
        if len(sys.argv) == 2 and sys.argv[1] == "console":
            curses.wrapper(console, sensors)
        else:
            text_console(sensors)

if __name__ == "__main__":
    main()
