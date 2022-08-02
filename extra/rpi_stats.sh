#!/bin/bash
vcgencmd measure_temp
vcgencmd get_throttled
vcgencmd measure_volts
vcgencmd get_mem arm
vcgencmd get_mem gpu
