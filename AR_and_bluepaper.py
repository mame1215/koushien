import time

import cv2

import color_flight
from color_flight import ColorUserApi

from ar_flight import ARUserApi


# 最初の着陸地点から青画用紙までの移動量（cm）
DIFFERENCE_X = 50
DIFFERENCE_Y = 0


class ARColorUserApi(ARUserApi, ColorUserApi):
    pass


def land(api):
    print("着陸コマンドを送信します", flush=True)
    try:
        result = api.single_fly_touchdown()
        print(f"着陸コマンド完了: {result}", flush=True)
        return True
    except Exception as error:
        print(f"着陸コマンドで例外が発生しました: {error!r}", flush=True)
        return False


def main():
    api = ARColorUserApi()
    if not api.connect():
        print("connect error")
        return

    print("connection to station by wifi")
    print(f"battery={api.get_battery()}")

    api.Plane_cmd_swith_rtp(0)
    api.single_fly_flip_rtp()
    time.sleep(3)

    first_landing_complete = False
    try:
        api.Plane_cmd_camera_angle(1, 90)
        print("最初の着陸地点へ移動します")
        api.single_fly_takeoff()
        api.single_fly_up(20)
        api.single_fly_optical_flow_descent(
            target_height_cm=0,
            alignment_count=3,
        )
    finally:
        first_landing_complete = land(api)

    if not first_landing_complete:
        return

    print("着陸完了、10秒待機します")
    time.sleep(10)

    try:
        print("青画用紙へ向けて再び浮上します")
        api.single_fly_takeoff()
        api.single_fly_straight_flight(DIFFERENCE_X, DIFFERENCE_Y, -10)

        print("青い画用紙の真上へ移動し、向きを合わせます")
        color_flight.SHOW_COLOR_DEBUG = True
        result = api.single_fly_color_overhead(
            "blue",
            align_orientation=True,
            angle_tolerance_deg=5.0,
        )
        if result is None or not result.get("aligned", False):
            print("青画用紙の真上まで到達できませんでした。現在位置で着陸します")
            return

        print("青い画用紙の真上に到着しました")
    finally:
        land(api)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()