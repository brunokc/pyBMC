
import sys
import datetime

logfile = open("pybmc.log", "a+")
sys.stdout = logfile
sys.stderr = logfile

def log(*args):
    def _get_timestamp():
        now = datetime.datetime.now()
        milliseconds = round(now.microsecond / 1000)
        return f"{now.strftime('%Y-%m-%d %H:%M:%S')}.{milliseconds:03}: "

    print(_get_timestamp(), *args)
