import time

import cv2

import python_files.color_flight as color_flight
from python_files.color_flight import ColorUserApi


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

    try:
        print("浮上します")
        api.single_fly_takeoff()
        api.single_fly_up(20)
        api.single_fly_hover_flight(2)

        print("青い画用紙の真上へ移動します")
        color_flight.SHOW_COLOR_DEBUG = True
        result = api.single_fly_color_overhead(
            "blue",
            align_orientation=True,
            angle_tolerance_deg=5.0,
        )
        if result is None or not result.get("aligned", False):
            print("真上まで到達できませんでした。現在位置で着陸します")
            return

        print("青い画用紙の真上に到着しました")
    finally:
        print("着陸コマンドを送信します", flush=True)
        try:
            touchdown_result = api.single_fly_touchdown()
            print(f"着陸コマンド完了: {touchdown_result}", flush=True)
        except Exception as error:
            print(f"着陸コマンドで例外が発生しました: {error!r}", flush=True)
        finally:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()