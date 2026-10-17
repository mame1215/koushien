##0番のARに着陸後、赤い画用紙上に着陸

import pyhula
import math


import time

import cv2
from python_files.color_flight import ColorUserApi


#ARからの赤画用紙の位置
DIFFERENCE_X = 50
DIFFERENCE_Y = 0

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

    api.Plane_cmd_camera_angle(1,90)

    print("浮上")
    api.single_fly_takeoff()

    #api.single_fly_hover_flight(3)

    api.single_fly_up(20)

    api.single_fly_Optical_flow_alignment(0,20,0)

    api.single_fly_down(20)

    api.single_fly_Optical_flow_alignment(0,20,0)

    api.single_fly_down(60)

    api.single_fly_Optical_flow_alignment(0,20,0)

    api.single_fly_touchdown()
    print("着陸完了, 10s待機")

    time.sleep(10)

    try:
        print("浮上します")
        api.single_fly_takeoff()
        api.single_fly_straight_flight(DIFFERENCE_X, DIFFERENCE_Y,-10)

        print("赤い画用紙の真上へ移動します")
        api.single_fly_camera_down()
        # 一時的な安全確認。各移動の前に推定量を表示して y 入力を求める。
        #result = api.single_fly_color_overhead(
        #    "red", confirm_before_move=True
        #)
        result = api.single_fly_color_overhead("red")
        if result is None or not result.get("aligned", False):
            print("真上まで到達できなかったため、その場で着陸します")
            return

        print("赤い画用紙の真上に到着しました")
    finally:
        #cv2.destroyAllWindows()
        print("着陸コマンドを送信します", flush=True)
        try:
            touchdown_result = api.single_fly_touchdown()
            print(f"着陸コマンド完了: {touchdown_result}", flush=True)
        except Exception as error:
            print(f"着陸コマンドで例外が発生しました: {error!r}", flush=True)

if __name__ == "__main__":
    main()