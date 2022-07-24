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

from Sensors import *

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
        stdscr.addstr(6, 10, f"Humidity: {temp.humidity:.1f}%")

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
