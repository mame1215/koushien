import pyhula
import time

import color_flight
from color_flight import ColorUserApi

from ar_flight import ARUserApi

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
