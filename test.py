import pyhula
import time

import python_files.color_flight as color_flight
from python_files.color_flight import ColorUserApi

from python_files.ar_flight import ARUserApi

class ARColorUserApi(ARUserApi, ColorUserApi):
    pass

api = ARColorUserApi()
if not api.connect():
    print("connect error")
else:
    print("connection to station by wifi")

print(f"battery={api.get_battery()}")

api.single_fly_takeoff()

time.sleep(3)

api.single_fly_touchdown()
