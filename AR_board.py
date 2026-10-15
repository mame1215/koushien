import pyhula
import time
import math

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

# ストリームを有効化（この順番が重要）
api.Plane_cmd_swith_rtp(0)
api.single_fly_flip_rtp()

# SPS/PPSが届くまで待機
time.sleep(3)

api.single_fly_takeoff()

api.Plane_cmd_camera_angle(1,0)

print("映像取得開始...")

api.single_fly_hover_flight(3)

ret = api.single_fly_Anticipatory_recognition(2)

if ret['result'] == True:
    api.single_fly_straight_flight(ret['x']-10,ret['y']-30,0,60)

    api.Plane_cmd_camera_angle(1,90)

    api.single_fly_hover_flight(3)

    api.single_fly_optical_flow_descent(20,2,3,50)

api.single_fly_touchdown()
