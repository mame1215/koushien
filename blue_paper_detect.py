import time

import cv2
import numpy as np

import python_files.color_flight as color_flight
from python_files.color_flight import ColorUserApi


WINDOW_NAME = "Hula camera - blue paper detection"


def show_blue_paper_location(frame):
    mask = color_flight._color_mask(frame, "blue")
    paper = color_flight._find_paper(frame, mask)
    view = frame.copy()

    if paper is None:
        cv2.putText(
            view,
            "BLUE PAPER NOT FOUND",
            (15, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 0, 0),
            2,
        )
    else:
        contour, corners, _ = paper
        center = corners.mean(axis=0)
        center_point = (int(center[0]), int(center[1]))
        polygon = np.asarray(corners, dtype=np.int32)

        cv2.drawContours(view, [contour], -1, (0, 255, 0), 3)
        cv2.polylines(view, [polygon], True, (255, 255, 0), 2)
        cv2.circle(view, center_point, 7, (255, 0, 0), -1)
        cv2.putText(
            view,
            f"BLUE PAPER: x={center_point[0]}, y={center_point[1]}",
            (15, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
        )

    cv2.imshow(WINDOW_NAME, cv2.cvtColor(view, cv2.COLOR_RGB2BGR))
    return cv2.waitKey(1) & 0xFF


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
        api.single_fly_camera_down()

        print("青い画用紙を検出します。終了するには映像ウィンドウで q を押してください")
        while True:
            frame = api.get_image_array()
            if frame is None or not hasattr(frame, "shape") or len(frame.shape) != 3:
                time.sleep(0.1)
                continue
            if show_blue_paper_location(frame) == ord("q"):
                break
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