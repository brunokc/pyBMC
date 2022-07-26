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
import requests
import json
from collections import namedtuple

import logger

HOST = "127.0.0.1"
PORT = 5000

class SensorClient:
    def __init__(self, host, port):
        self._host = host
        self._port = port
        self._base_uri = f"http://{host}:{port}"
        self.update_state()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def update_state(self):
        response = requests.get(self._base_uri + "/api/v1/state")
        state = response.json()

        resp_str = json.dumps(state, indent = 2)
        logger.log(f"response: {resp_str}")

        self._fans = []
        fans = state["fans"]
        for i in range(len(fans)):
            fan = self._build_fan(fans[i])
            self._fans.append(fan)

        self._temp = self._build_temp(state["tempSensor"])
        self._psu = self._build_psu(state["psu"])

    @property
    def fans(self):
        return self._fans

    @property
    def temp(self):
        return self._temp

    @property
    def psu(self):
        return self._psu

    def _build_fan(self, fan):
        base_uri = self._base_uri
        def set_speed(self, speed):
            if speed < 0 or speed > 100:
                raise RuntimeError(f"invalid fan speed {speed}")

            data = { "dutyCycle": speed }
            requests.patch(base_uri + f"/api/v1/fan/{self.id}", json = data)

        Fan = namedtuple("Fan", fan.keys())
        Fan.set_speed = set_speed
        return Fan(**fan)

    @staticmethod
    def _build_temp(temp):
        TemperatureHumiditySensor = namedtuple("TemperatureHumiditySensor", temp.keys())
        return TemperatureHumiditySensor(**temp)

    @staticmethod
    def _build_psu(psu):
        Psu = namedtuple("Psu", psu.keys())
        return Psu(**psu)

def console(stdscr, sensors):
    # Hide cursor
    curses.curs_set(0)
    # Non blocking input (getch)
    stdscr.nodelay(True)

    selected_fan = 0
    sensor_update_time = 0.2
    wait_time = 0.05

    accumulated_time = 0
    while True:
        accumulated_time += wait_time
        if accumulated_time >= sensor_update_time:
            sensors.update_state()
            accumulated_time = 0

        fans = sensors.fans
        stdscr.addstr(0, 40, "  PyBMC v0.1  ", curses.A_REVERSE)
        stdscr.addstr(2,  9, f" Fan 1 speed: {int(fans[0].rpm)} rpm  ")
        stdscr.addstr(3,  9, f" Fan 1 PWM: {fans[0].dutyCycle}%  ", curses.A_REVERSE if selected_fan == 0 else curses.A_NORMAL)
        stdscr.addstr(2, 39, f" Fan 2 speed: {int(fans[1].rpm)} rpm  ")
        stdscr.addstr(3, 39, f" Fan 2 PWM: {fans[1].dutyCycle}%  ", curses.A_REVERSE if selected_fan == 1 else curses.A_NORMAL)
        stdscr.addstr(2, 69, f" Fan 3 speed: {int(fans[2].rpm)} rpm  ")
        stdscr.addstr(3, 69, f" Fan 3 PWM: {fans[2].dutyCycle}%  ", curses.A_REVERSE if selected_fan == 2 else curses.A_NORMAL)

        temp = sensors.temp
        temperatureF = 32 + temp.temperatureC * 9 / 5
        stdscr.addstr(5, 10, f"Temperature: {temp.temperatureC:.1f}C ({temperatureF:.1f}F)")
        stdscr.addstr(6, 10, f"Humidity: {temp.humidity:.1f}%")

        psu = sensors.psu
        psu_state = "on" if psu.powerState else "off"
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
            duty_cycle = fans[selected_fan].dutyCycle
            duty_cycle = duty_cycle + 10 if duty_cycle < 100 else 100
            fans[selected_fan].set_speed(duty_cycle)
        elif c == curses.KEY_DOWN:
            duty_cycle = fans[selected_fan].dutyCycle
            duty_cycle = duty_cycle - 10 if duty_cycle > 0 else 0
            fans[selected_fan].set_speed(duty_cycle)
        elif c == ord('t') or c == ord('T'):
            pass
        elif c != curses.ERR:
            break

        time.sleep(wait_time)


def dump_data(sensors):
    fans = sensors.fans
    logger.log(f"Fan 1: {int(fans[0].rpm)} rpm")
    logger.log(f"Fan 2: {int(fans[1].rpm)} rpm")
    logger.log(f"Fan 3: {int(fans[2].rpm)} rpm")

    temp = sensors.temp
    logger.log(f"Temperature: {temp.temperature_c:.1f}C ({temp.temperature_f:.1f}F)")
    logger.log(f"Humidity: {temp.humidity}%")

    psu_state = "on" if sensors.psu.ps_ok.state else "off"
    logger.log(f"PSU Ok: {psu_state}")
    logger.log()

def text_console(sensors):
    sensors.psu.power_switch.toggle()
    while True:
        sensors.update_state()
        dump_data(sensors)
        time.sleep(1)

def main():
    with SensorClient(HOST, PORT) as sensors:
        if len(sys.argv) == 2 and sys.argv[1] == "debug":
            text_console(sensors)
        else:
            curses.wrapper(console, sensors)

if __name__ == "__main__":
    main()
