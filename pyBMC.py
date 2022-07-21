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
import RPi.GPIO as GPIO

import board
import adafruit_dht

# Noctua specifies 25Khz frequency for PWM control
PWM_FREQUENCY = 25000

fans = [
    {
        "name": "fan1",
        "rpmPin": 17,
        "pwmPin": 18
    },
    {
        "name": "fan2",
        "rpmPin": 23,
        "pwmPin": 24
    },
    {
        "name": "fan3",
        "rpmPin": 16,
        "pwmPin": 20
    },
]

temp = {
    "name": "temp1",
    "pin": board.D21
}

psu = {
    "ps_on": {
        "pin": 25,
        "mode": GPIO.OUT
    },
    "ps_ok": {
        "pin": 27,
        "mode": GPIO.IN
    }
}


def on_rpm_falling_edge(n):
    pass

def setup_pins():
    GPIO.setmode(GPIO.BCM)
    #GPIO.setwarnings(False)

    # Temp probe
    temp["sensor"] = adafruit_dht.DHT22(temp["pin"])

    # Fan pins
    for fan in fans:
        fanPin = fan["rpmPin"]
        GPIO.setup(fanPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(fanPin, GPIO.FALLING, on_rpm_falling_edge)

        GPIO.setup(fan["pwmPin"], GPIO.OUT, initial=GPIO.LOW)

    # PSU pins
    for name, pin in psu:
        if pin["mode"] == GPIO.IN:
            GPIO.setup(pin["pin"], pin["mode"], pull_up_down=GPIO.PUD_UP)
        else:
            GPIO.setup(pin["pin"], pin["mode"], initial=GPIO.LOW)


def main():
    setup_pins()


if __name__ == "__main__":
    main()
