
import datetime

logfile = open("pybmc.log", "a+")

def log(*args):
    def _get_timestamp():
        now = datetime.datetime.now()
        milliseconds = round(now.microsecond / 1000)
        return f"{now.strftime('%Y-%m-%d %H:%M:%S')}.{milliseconds:03}: "

    logfile.write(_get_timestamp() + str(*args) + "\n")
