
import subprocess
import re
from . import logger

def _run_command(cmd):
    output = subprocess.check_output(cmd, stderr = subprocess.PIPE).decode("utf-8")
    return output

def _process_commands(commands):
    results = { }
    for cmd in commands:
        # logger.log(f"Command: {cmd['cmd']}")
        output = _run_command(cmd["cmd"])
        # logger.log(f"Output: {output}")
        for line in output.splitlines():
            # logger.log(f"Line: {line}")
            match = cmd["re"].search(line)
            if match:
                value = match.group(1)
                # logger.log(f"Value: {value}")
                if "converter" in cmd and cmd["converter"]:
                    value = cmd["converter"](value)
                    # logger.log(f"Converted value: {value}")
                results[cmd["name"]] = value
                break

    return results

# Return static data (data we don't expect to change)
def get_system_info():
    commands = [
        {
            "name": "model",
            "cmd": ["cat", "/proc/cpuinfo"],
            "re": re.compile("Model\s+:\s(.+)"),
        },
        {
            "name": "totalMem",
            "cmd": ["vcgencmd", "get_config", "int"],
            "re": re.compile("total_mem=(\d+)"),
            "converter": lambda x: int(x),
        },
        {
            "name": "cpuMem",
            "cmd": ["vcgencmd", "get_mem", "arm"],
            "re": re.compile("arm=(\d+)M"),
            "converter": lambda x: int(x),
        },
        {
            "name": "gpuMem",
            "cmd": ["vcgencmd", "get_mem", "gpu"],
            "re": re.compile("gpu=(\d+)M"),
            "converter": lambda x: int(x),
        },
        # TODO:
        # - uptime: /proc/uptime?
        #   - Can we use a bar graph?
        # - Parse uptime a bit better
        # - Memory: bar graph (green/red) for available/used?
    ]

    return {
        "systemInfo": _process_commands(commands)
    }

def get_system_stats():
    commands = [
        {
            "name": "cpuTemp",
            "cmd": ["vcgencmd", "measure_temp"],
            "re": re.compile("^temp=([\d\.]+)'C"),
            "converter": lambda x: float(x),
        },
        {
            "name": "throttled",
            "cmd": ["vcgencmd", "get_throttled"],
            "re": re.compile("throttled=0x([0-9a-fA-F]+)"),
            "converter": lambda x: int(x, 16),
        },
        {
            "name": "volts",
            "cmd": ["vcgencmd", "measure_volts"],
            "re": re.compile("volt=([\d.]+)V"),
            "converter": lambda x: float(x),
        },
        {
            "name": "uptime",
            "cmd": ["cat", "/proc/uptime"],
            "re": re.compile("^([\d.]+)"),
            # "converter": uptime_converter,
        },
        # TODO:
        # - uptime: /proc/uptime?
        #   - Can we use a bar graph?
        # - Parse uptime a bit better
        # - Memory: bar graph (green/red) for available/used?
    ]

    return {
        "systemStats": _process_commands(commands)
    }
