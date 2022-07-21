#
# pyBMC
#
# Based on the work of DriftKingTW
# (https://blog.driftking.tw/en/2019/11/Using-Raspberry-Pi-to-Control-a-PWM-Fan-and-Monitor-its-Speed/)
#

import sys
import time
import curses

import RPi.GPIO as GPIO

import board
import adafruit_dht

# Noctua specifies 25Khz frequency for PWM control.
# For RPM reading, it says there's two pulses per rotation
# (https://noctua.at/pub/media/wysiwyg/Noctua_PWM_specifications_white_paper.pdf)
PWM_FREQUENCY = 25000
PULSES_PER_ROTATION = 2
HZ_TO_RPM = 60 / PULSES_PER_ROTATION

class Fan:
    tally_time = 1

    def __init__(self, name, rpm_pin, pwm_pin) -> None:
        self.name = name
        self.rpm_pin = rpm_pin
        self.pwm_pin = pwm_pin
        self._rpm = 0
        self._pwm = 100
        self._pwm_device = None
        self._ticks = 0
        self._lastTallyTime = 0

        log(f"Setting up GPIOs for fan {self.name}...")
        log(f"   RPM pin: {self.rpm_pin}")
        GPIO.setup(self.rpm_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        def rpm_callback(pin):
            self.on_rpm_pin_falling_edge(pin)

        GPIO.add_event_detect(self.rpm_pin, GPIO.FALLING, rpm_callback)

        log(f"   PWM pin: {self.pwm_pin}")
        GPIO.setup(self.pwm_pin, GPIO.OUT, initial=GPIO.LOW)
        self._pwm_device = GPIO.PWM(self.pwm_pin, PWM_FREQUENCY)
        self._lastTallyTime = time.time()
        self._pwm_device.start(self._pwm)

    def stop(self):
        if self._pwm_device:
            self._pwm_device.stop()
        GPIO.remove_event_detect(self.rpm_pin)

    def __del__(self):
        log(f"__del__ for fan {self.name}")
        self.stop()
        del self._pwm_device

    def reset(self):
        self._rpm = 0
        self._ticks = 0
        self._lastTallyTime = 0

    def on_rpm_pin_falling_edge(self, pin):
        if self.rpm_pin != pin:
            raise RuntimeError("on_rpm_pin_falling_edge: rpm pin doesn't match")

        self._ticks += 1
        now = time.time()
        dt = now - self._lastTallyTime
        if dt > Fan.tally_time:
            freq = self._ticks / dt
            self._rpm = freq * HZ_TO_RPM
            self._ticks = 0
            self._lastTallyTime = now


    @property
    def rpm(self):
        return self._rpm

    @property
    def pwm(self):
        return self._pwm

    def set_speed(self, speed):
        self._pwm_device.ChangeDutyCycle(speed)
        self._pwm = speed


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

    def __del__(self):
        log(f"__del__ for temp {self._name}")
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
    def __init__(self, name, pin, mode) -> None:
        self._name = name
        self._pin = pin
        self._mode = mode
        self._state = GPIO.LOW

        if self._mode == GPIO.IN:
            GPIO.setup(self._pin, self._mode, pull_up_down=GPIO.PUD_DOWN)
        else:
            GPIO.setup(self._pin, self._mode, initial=GPIO.LOW)

    def update_state(self):
        if self._mode == GPIO.OUT:
            raise RuntimeError("update_state is invalid on an output pin")

        self._state = GPIO.input(self._pin)

    @property
    def state(self):
        return self._state

    def read(self):
        if self._mode == GPIO.OUT:
            raise RuntimeError("read is invalid on an output pin")
        return self._state

    def write(self, value):
        if self._mode == GPIO.IN:
            raise RuntimeError("write is invalid on an input pin")

        GPIO.output(self._pin, value)
        self._state = value

    def toggle(self):
        if self._mode == GPIO.IN:
            raise RuntimeError("toggle is invalid on an input pin")

        new_state = GPIO.LOW if self._state else GPIO.HIGH
        self.write(new_state)


class Psu:
    def __init__(self) -> None:
        self.power_switch = PsuPin("ps_switch", 25, GPIO.OUT)
        self.ps_ok = PsuPin("ps_ok", 27, GPIO.IN)

    def update_state(self):
        self.ps_ok.update_state()


class Sensors:
    def __init__(self) -> None:
        GPIO.setmode(GPIO.BCM)
        #GPIO.setwarnings(False)

        self.fans = [
            Fan("fan1", rpm_pin = 18, pwm_pin = 17),
            Fan("fan2", rpm_pin = 23, pwm_pin = 24),
            Fan("fan3", rpm_pin = 16, pwm_pin = 20),
        ]
        self.temp = TempHumiditySensor("temp1", board.D21)
        self.psu = Psu()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        del self.psu
        del self.temp
        for fan in self.fans:
            fan.stop()
        GPIO.cleanup()

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
        stdscr.addstr(3,  9, f" Fan 1 PWM: {fans[0].pwm}%  ", curses.A_REVERSE if selected_fan == 0 else curses.A_NORMAL)
        stdscr.addstr(2, 39, f" Fan 2 speed: {int(fans[1].rpm)} rpm  ")
        stdscr.addstr(3, 39, f" Fan 2 PWM: {fans[1].pwm}%  ", curses.A_REVERSE if selected_fan == 1 else curses.A_NORMAL)
        stdscr.addstr(2, 69, f" Fan 3 speed: {int(fans[2].rpm)} rpm  ")
        stdscr.addstr(3, 69, f" Fan 3 PWM: {fans[2].pwm}%  ", curses.A_REVERSE if selected_fan == 2 else curses.A_NORMAL)

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
            pwm = fans[selected_fan].pwm
            pwm = pwm + 10 if pwm < 100 else 100
            fans[selected_fan].set_speed(pwm)
        elif c == curses.KEY_DOWN:
            pwm = fans[selected_fan].pwm
            pwm = pwm - 10 if pwm > 0 else 0
            fans[selected_fan].set_speed(pwm)
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
