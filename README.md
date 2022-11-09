# pyBMC

pyBMC is a Raspberry Pi based project written in Python that aims to approximate
the functionality of the [BMC (Baseboard Management Controller)](https://en.wikipedia.org/wiki/Intelligent_Platform_Management_Interface#Baseboard_management_controller) component
of an [IPMI](https://en.wikipedia.org/wiki/Intelligent_Platform_Management_Interface)
system. BMCs are specialized microcontroller embedded on server motherboards and
are used to remotely monitor and control it.

![pyBMC screenshot](images/pybmc-screenshot.png)

pyBMC does not intend to support the full set of functionality provided by a real
BMC. It does make use of IPMI's native remoting protocols (RMCP) either. Instead,
it exposes functionality through a web application and a web API.

## Features

The current version of pyBMC supports:

- Turning a system on and off (remote power switching)
- Read-only view of the "Power OK" signal from the power supply
- PWM speed control and RPM sensing for up to 3 12V fans
- Individual or synchronized PWM speed control of fans
- Temperature and humidity sensor for the monitored system
- Monitoring of Raspberry Pi state where pyBMC is running
  - System configuration (model, total memory, etc)
  - CPU temperature
  - CPU state (under-voltage, throtlling, temperature and frequency limiting flags)
  - Uptime

## Installation

From a Raspberry Pi SSH session, run this:
```
wget -qO - https://raw.githubusercontent.com/brunokc/pyBMC/main/setup_pybmc.sh | bash -
```
