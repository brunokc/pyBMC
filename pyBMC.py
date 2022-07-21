#
# pyBMC
#
# Based on the work of DriftKingTW
# (https://blog.driftking.tw/en/2019/11/Using-Raspberry-Pi-to-Control-a-PWM-Fan-and-Monitor-its-Speed/)
#

import sys
import os
import time
import signal
import atexit
import curses

import RPi.GPIO as GPIO

import board
import adafruit_dht

# Noctua specifies 25Khz frequency for PWM control
PWM_FREQUENCY = 25
PULSES_PER_ROTATION = 2

fans = [
    {
        "name": "fan1",
        "rpmPin": 17,
        "rpm": 0,
        "pwmPin": 18,
        "pwm": 100,
        "pwmDevice": None
    },
    {
        "name": "fan2",
        "rpmPin": 23,
        "rpm": 0,
        "pwmPin": 24,
        "pwm": 100,
        "pwmDevice": None
    },
    {
        "name": "fan3",
        "rpmPin": 16,
        "rpm": 0,
        "pwmPin": 20,
        "pwm": 100,
        "pwmDevice": None
    },
]

fan_by_rpm_pin = { }
for fan in fans:
    fan_by_rpm_pin[fan["rpmPin"]] = fan

temp = {
    "name": "temp1",
    "pin": board.D21,
    "device": None,
    "temp_c": 0,
    "temp_f": 0,
    "humidity": 0
}

psu = {
    "ps_switch": {
        "pin": 25,
        "mode": GPIO.OUT,
        "state": False
    },
    # "ps_on": {
    #     "pin": 6,
    #     "mode": GPIO.IN,
    #     "state": False
    # },
    "ps_ok": {
        "pin": 27,
        "mode": GPIO.IN,
        "state": False
    }
}

def log(*args):
    print(*args)

def cleanup():
    if temp["device"]:
        temp["device"].exit()
    GPIO.cleanup()


lastEventTime = time.time()
def on_rpm_falling_edge(pin):
    global lastEventTime

    log(f"on_rpm_falling_edge({pin})")
    dt = time.time() - lastEventTime
    # Reject spurious short pulses
    if dt < 0.005:
        return

    freq = 1 / dt
    rpm = freq * 60 / PULSES_PER_ROTATION
    fan_by_rpm_pin[pin]["rpm"] = rpm
    lastEventTime = time.time()


def setup_pins():
    GPIO.setmode(GPIO.BCM)
    #GPIO.setwarnings(False)

    # Temp probe
    log(f"Setting up GPIOs for temp probe...")
    temp["device"] = adafruit_dht.DHT22(temp["pin"])

    # Fan pins
    for fan in fans:
        log(f"Setting up GPIOs for fan {fan['name']}...")
        rpmPin = fan["rpmPin"]
        log(f"   RPM pin: {rpmPin}")
        GPIO.setup(rpmPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(rpmPin, GPIO.FALLING, on_rpm_falling_edge)

        pwmPin = fan["pwmPin"]
        log(f"   PWM pin: {pwmPin}")
        GPIO.setup(pwmPin, GPIO.OUT, initial=GPIO.LOW)
        fan["pwmDevice"] = GPIO.PWM(pwmPin, PWM_FREQUENCY)
        fan["pwmDevice"].start(0)

    # PSU pins
    log(f"Setting up GPIOs for PSU...")
    for _, pin in psu.items():
        if pin["mode"] == GPIO.IN:
            GPIO.setup(pin["pin"], pin["mode"], pull_up_down=GPIO.PUD_DOWN)
        else:
            GPIO.setup(pin["pin"], pin["mode"], initial=GPIO.LOW)


def set_fan_speed(fan, speed):
    fan.start(speed)

def update_psu_state():
    psok = psu["ps_ok"]
    psok["state"] = GPIO.input(psok["pin"])

def update_temp_state():
    dht = temp["device"]

    try:
        temp_c = dht.temperature
        temp_f = 32 + temp_c * 9 / 5
        humidity = dht.humidity
    except RuntimeError:
        temp_c = 0
        temp_f = 0
        humidity = 0

    temp["temp_c"] = temp_c
    temp["temp_f"] = temp_f
    temp["humidity"] = humidity

def toggle_power():
    switch = psu["ps_switch"]
    new_state = GPIO.LOW if switch["state"] else GPIO.HIGH
    GPIO.output(switch["pin"], new_state)
    switch["state"] = True if new_state else False

def console(stdscr):
    curses.curs_set(0)

    while True:
        update_psu_state()
        update_temp_state()

        stdscr.addstr(0, 30, "PyBMC v0.1", curses.A_REVERSE)
        stdscr.addstr(2, 10, f"Fan 1: {fans[0]['rpm']} rpm")
        stdscr.addstr(2, 30, f"Fan 2: {fans[1]['rpm']} rpm")
        stdscr.addstr(2, 50, f"Fan 3: {fans[2]['rpm']} rpm")

        stdscr.addstr(4, 10, f"Temperature: {temp['temp_c']:.1f}C ({temp['temp_f']:.1f}F)")
        stdscr.addstr(4, 50, f"Humidity: {temp['humidity']}%")

        psok = psu["ps_ok"]
        psu_state = "on" if psok['state'] else "off"
        stdscr.addstr(6, 10, f"PSU Ok: {psu_state}")

        stdscr.refresh()
        time.sleep(0.1)

        c = stdscr.getch()
        if c == ord('P') or c == ord('p'):
            toggle_power()
        elif c != curses.ERR:
            break

def dump_data():
    log(f"Fan 1: {fans[0]['rpm']} rpm")
    log(f"Fan 2: {fans[1]['rpm']} rpm")
    log(f"Fan 3: {fans[2]['rpm']} rpm")

    log(f"Temperature: {temp['temp_c']:.1f}C ({temp['temp_f']:.1f}F)")
    log(f"Humidity: {temp['humidity']}%")

    psok = psu["ps_ok"]
    psu_state = "on" if psok['state'] else "off"
    log(f"PSU Ok: {psu_state}")
    log()

def text_console():
    toggle_power()
    while True:
        update_psu_state()
        update_temp_state()

        dump_data()
        time.sleep(1)

def main():
    atexit.register(cleanup)
    setup_pins()

    if len(sys.argv) == 2 and sys.argv[1] == "console":
        curses.wrapper(console)
    else:
        text_console()

if __name__ == "__main__":
    main()
