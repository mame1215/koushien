import pyhula
import time
import math

import python_files.color_flight as color_flight
from python_files.color_flight import ColorUserApi

from python_files.ar_flight import ARUserApi

class ARColorUserApi(ARUserApi, ColorUserApi):
    pass


def main():
    api = ColorUserApi()
    if not api.connect():
        print("connect error")
        return

    print("connection to station by wifi")
    print(f"battery={api.get_battery()}")

    api.Plane_cmd_swith_rtp(0)
    api.single_fly_flip_rtp()
    time.sleep(3)

    api.single_fly_takeoff()
    api.single_fly_color_overhead("green",2)

    api.single_fly_touchdown()



if __name__ == "__main__":
    main()