import argparse
import math
import time

import cv2
import numpy as np
import pyhula


CAMERA_HORIZONTAL_FOV_DEG = 40.0
CAMERA_VERTICAL_FOV_DEG = 40.0
CAMERA_DOWN_ANGLE_DEG = 90
# カメラが機体中心より前方にある距離。機体中心を色紙の真上に合わせる補正。
CAMERA_FORWARD_OFFSET_CM = 5.0
# 後退は実移動量が大きくなりやすいため、後退指令だけを校正する。
BACKWARD_MOVE_SCALE = 0.20
# 真上に入った後、低い高度でもう一度位置を確認するための降下量。
COLOR_ALIGNMENT_DESCENT_CM = 20
# get_image_array()の画像下方向を、機体の前方向として扱う。
IMAGE_DOWN_IS_FORWARD = False
SHOW_COLOR_DEBUG = False
COLOR_RANGES = {
    "red": ((0, 152, 64), (9, 255, 204), (179, 153, 64), (179, 254, 248)),
    "yellow": ((18, 35, 30), (40, 255, 255), None, None),
    "green": ((35, 35, 89), (101, 255, 177), None, None),
    "blue": ((82, 94, 95), (179, 211, 141), None, None),
}
#色画用紙の上に移動するとき、認識した距離と移動する距離の割合
COLOR_MOVING_RATE = 0.6


def _color_mask(frame, color, color_range=None):
    if color not in COLOR_RANGES:
        raise ValueError(
            f"unknown color: {color!r}; choose one of {list(COLOR_RANGES)}"
        )

    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
    first_low, first_high, second_low, second_high = (
        COLOR_RANGES[color] if color_range is None else color_range
    )
    mask = cv2.inRange(
        hsv,
        np.array(first_low, dtype=np.uint8),
        np.array(first_high, dtype=np.uint8),
    )
    if second_low is not None:
        mask |= cv2.inRange(
            hsv,
            np.array(second_low, dtype=np.uint8),
            np.array(second_high, dtype=np.uint8),
        )

    kernel = np.ones((3, 3), dtype=np.uint8)
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)


def _find_paper(frame, mask):
    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    if not contours:
        return None

    contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(contour)
    height, width = frame.shape[:2]
    if area < width * height * 0.001:
        return None

    perimeter = cv2.arcLength(contour, True)
    corners = cv2.approxPolyDP(contour, 0.04 * perimeter, True)
    if len(corners) != 4:
        corners = cv2.boxPoints(cv2.minAreaRect(contour))
    corners = np.asarray(corners, dtype=np.float32).reshape(4, 2)

    center = corners.mean(axis=0)
    corners = corners[
        np.argsort(
            np.arctan2(corners[:, 1] - center[1], corners[:, 0] - center[0])
        )
    ]
    return contour, corners, area


def _paper_angle_deg(corners):
    edges = np.roll(corners, -1, axis=0) - corners
    lengths = np.linalg.norm(edges, axis=1)
    edge = edges[int(np.argmax(lengths))]
    angle = math.degrees(math.atan2(float(edge[1]), float(edge[0])))
    return ((angle + 90.0) % 180.0) - 90.0


def _movement_from_center(error_x, error_y, frame_shape, height_cm):
    frame_height, frame_width = frame_shape[:2]
    angle_x = math.atan(
        (error_x / (frame_width / 2))
        * math.tan(math.radians(CAMERA_HORIZONTAL_FOV_DEG / 2))
    )
    angle_y = math.atan(
        (error_y / (frame_height / 2))
        * math.tan(math.radians(CAMERA_VERTICAL_FOV_DEG / 2))
    )
    move_x = height_cm * math.tan(angle_x)
    move_y = height_cm * math.tan(angle_y)
    if not IMAGE_DOWN_IS_FORWARD:
        move_y = -move_y
    move_y += CAMERA_FORWARD_OFFSET_CM
    if move_y < 0:
        move_y *= BACKWARD_MOVE_SCALE
    return move_x, move_y


def _show_color_debug(frame, target, mask):
    view = frame.copy()
    height, width = view.shape[:2]
    cv2.drawMarker(
        view, (width // 2, height // 2), (255, 255, 255),
        cv2.MARKER_CROSS, 30, 2,
    )
    if target is None:
        cv2.putText(
            view, "NOT FOUND", (15, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2,
        )
    else:
        contour = target["contour"]
        corners = np.array(target["corners"], dtype=np.int32)
        cv2.drawContours(view, [contour], -1, (0, 255, 0), 3)
        cv2.polylines(view, [corners], True, (255, 255, 0), 2)
        cv2.circle(view, target["center"], 7, (255, 0, 0), -1)
        cv2.putText(
            view, f"area={target['area_ratio']:.3f}", (15, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2,
        )
        for index, point in enumerate(target["corners"]):
            cv2.putText(
                view, str(index + 1), point,
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2,
            )

    cv2.imshow(
        "Hula camera - color detection",
        cv2.cvtColor(view, cv2.COLOR_RGB2BGR),
    )
    cv2.imshow("Hula color mask", mask)
    return cv2.waitKey(1) & 0xFF


class ColorUserApi(pyhula.UserApi):
    def single_fly_camera_down(self):
        """カメラを機体の真下へ向ける。"""
        result = self.Plane_cmd_camera_angle(1, CAMERA_DOWN_ANGLE_DEG)
        time.sleep(2)
        return result

    def single_fly_color_detect(self, color="blue"):
        """指定色の画用紙を検出し、移動量と旋回角を返す。機体は動かさない。"""
        frame = self.get_image_array()
        result = {
            "success": False,
            "aligned": False,
            "color": color,
            "move_x_cm": 0.0,
            "move_y_cm": 0.0,
            "turn_deg": 0.0,
        }
        if frame is None or not hasattr(frame, "shape") or len(frame.shape) != 3:
            print(f"色紙検出失敗: {color}, 映像フレームなし", flush=True)
            return result

        mask = _color_mask(frame, color)
        paper = _find_paper(frame, mask)
        if paper is None:
            if SHOW_COLOR_DEBUG:
                _show_color_debug(frame, None, mask)
            print(f"色紙検出失敗: {color}", flush=True)
            return result

        contour, corners, area = paper
        height, width = frame.shape[:2]
        center = corners.mean(axis=0)
        error_x = float(center[0] - width / 2)
        error_y = float(center[1] - height / 2)
        height_cm = float(self.get_plane_distance())
        move_x, move_y = _movement_from_center(
            error_x, error_y, frame.shape, height_cm
        )
        result.update(
            {
                "success": True,
                "aligned": False,
                "center": (int(center[0]), int(center[1])),
                "corners": [(int(x), int(y)) for x, y in corners],
                "area_ratio": area / (width * height),
                "move_x_cm": move_x,
                "move_y_cm": move_y,
                "turn_deg": _paper_angle_deg(corners),
                "contour": contour,
                "mask": mask,
            }
        )
        if SHOW_COLOR_DEBUG:
            _show_color_debug(frame, result, mask)
        print(
            f"色紙検出成功: 色={color}, "
            f"右={move_x:.1f}cm, 前={move_y:.1f}cm, "
            f"旋回目安={result['turn_deg']:.1f}度",
            flush=True,
        )
        return result

    def single_fly_color_tune(self, color="blue"):
        """飛行せずに映像を表示し、指定色のHSV範囲を調整する。"""
        if color not in COLOR_RANGES:
            raise ValueError(
                f"unknown color: {color!r}; choose one of {list(COLOR_RANGES)}"
            )

        control_window = f"HSV controls - {color}"
        video_window = f"Hula color tuning - {color}"
        mask_window = f"Color mask - {color}"
        initial_range = COLOR_RANGES[color]
        trackbars = [
            ("H min", initial_range[0][0], 179),
            ("S min", initial_range[0][1], 255),
            ("V min", initial_range[0][2], 255),
            ("H max", initial_range[1][0], 179),
            ("S max", initial_range[1][1], 255),
            ("V max", initial_range[1][2], 255),
        ]
        if initial_range[2] is not None:
            trackbars.extend(
                [
                    ("H2 min", initial_range[2][0], 179),
                    ("S2 min", initial_range[2][1], 255),
                    ("V2 min", initial_range[2][2], 255),
                    ("H2 max", initial_range[3][0], 179),
                    ("S2 max", initial_range[3][1], 255),
                    ("V2 max", initial_range[3][2], 255),
                ]
            )

        cv2.namedWindow(control_window, cv2.WINDOW_NORMAL)
        cv2.namedWindow(video_window, cv2.WINDOW_NORMAL)
        cv2.namedWindow(mask_window, cv2.WINDOW_NORMAL)
        for name, value, maximum in trackbars:
            cv2.createTrackbar(name, control_window, value, maximum, lambda _: None)

        print(
            f"{color} のしきい値を調整中です。終了は映像ウィンドウで q または Esc。"
            "機体の飛行操作は行いません。",
            flush=True,
        )
        current_range = initial_range
        try:
            while True:
                values = [
                    cv2.getTrackbarPos(name, control_window)
                    for name, _, _ in trackbars
                ]
                current_range = (
                    tuple(values[0:3]),
                    tuple(values[3:6]),
                    tuple(values[6:9]) if len(values) == 12 else None,
                    tuple(values[9:12]) if len(values) == 12 else None,
                )

                frame = self.get_image_array()
                if frame is None or not hasattr(frame, "shape") or len(frame.shape) != 3:
                    waiting_view = np.zeros((360, 640, 3), dtype=np.uint8)
                    cv2.putText(
                        waiting_view, "WAITING FOR HULA VIDEO...", (25, 150),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2,
                    )
                    cv2.putText(
                        waiting_view, "Press q or Esc to exit", (25, 195),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2,
                    )
                    cv2.imshow(video_window, waiting_view)
                    key = cv2.waitKeyEx(1) & 0xFF
                    if key in (ord("q"), 27):
                        break
                    try:
                        if cv2.getWindowProperty(
                            video_window, cv2.WND_PROP_VISIBLE
                        ) < 1:
                            break
                    except cv2.error:
                        break
                    time.sleep(0.05)
                    continue

                mask = _color_mask(frame, color, current_range)
                paper = _find_paper(frame, mask)
                view = frame.copy()
                if paper is None:
                    status = f"{color.upper()} PAPER NOT FOUND"
                    status_color = (255, 0, 0)
                else:
                    contour, corners, area = paper
                    center = corners.mean(axis=0)
                    center_point = (int(center[0]), int(center[1]))
                    polygon = np.asarray(corners, dtype=np.int32)
                    cv2.drawContours(view, [contour], -1, (0, 255, 0), 3)
                    cv2.polylines(view, [polygon], True, (255, 255, 0), 2)
                    cv2.circle(view, center_point, 7, (255, 0, 0), -1)
                    status = (
                        f"{color.upper()} FOUND x={center_point[0]} "
                        f"y={center_point[1]} area={area:.0f}"
                    )
                    status_color = (0, 255, 0)

                cv2.putText(
                    view, status, (15, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, status_color, 2,
                )
                cv2.imshow(video_window, cv2.cvtColor(view, cv2.COLOR_RGB2BGR))
                cv2.imshow(mask_window, mask)
                key = cv2.waitKeyEx(1) & 0xFF
                if key in (ord("q"), 27):
                    break
                try:
                    if cv2.getWindowProperty(
                        video_window, cv2.WND_PROP_VISIBLE
                    ) < 1:
                        break
                except cv2.error:
                    break
        finally:
            for window in (control_window, video_window, mask_window):
                try:
                    cv2.destroyWindow(window)
                except cv2.error:
                    pass

        print(
            f"{color}: {current_range!r}\n"
            f'COLOR_RANGES["{color}"] = {current_range!r}',
            flush=True,
        )
        return current_range

    def single_fly_color_overhead(
        self,
        color="red",
        tolerance_cm=3.0,
        max_iterations=8,
        confirm_before_move=False,
        align_orientation=False,
        angle_tolerance_deg=5.0,
    ):
        """指定色の画用紙の真上へ移動し、必要なら向きも合わせる。"""
        self.single_fly_camera_down()
        last_result = None
        descent_realign_done = False
        for iteration in range(1, max_iterations + 1):
            last_result = self.single_fly_color_detect(color)
            if not last_result["success"]:
                return last_result

            move_x = last_result["move_x_cm"]
            move_y = last_result["move_y_cm"]
            print(
                f"移動確認 {iteration}/{max_iterations}: "
                f"右={move_x:.1f}cm, 前={move_y:.1f}cm "
                f"(許容範囲={tolerance_cm:.1f}cm)",
                flush=True,
            )
            position_aligned = (
                abs(move_x) <= tolerance_cm and abs(move_y) <= tolerance_cm
            )
            if position_aligned:
                if not descent_realign_done:
                    print(
                        f"位置合わせ後に高度を{COLOR_ALIGNMENT_DESCENT_CM}cm下げ、"
                        "再度位置を合わせます",
                        flush=True,
                    )
                    self.single_fly_down(COLOR_ALIGNMENT_DESCENT_CM)
                    self.single_fly_hover_flight(1)
                    descent_realign_done = True
                    continue

                turn_deg = last_result["turn_deg"]
                if (
                    not align_orientation
                    or abs(turn_deg) <= angle_tolerance_deg
                ):
                    print("画用紙の真上・向き合わせ完了", flush=True)
                    last_result["aligned"] = True
                    last_result["orientation_aligned"] = (
                        not align_orientation
                        or abs(turn_deg) <= angle_tolerance_deg
                    )
                    return last_result

                turn_amount = max(1, int(round(abs(turn_deg))))
                turn_direction = (
                    "single_fly_turnright"
                    if turn_deg > 0
                    else "single_fly_turnleft"
                )
                print(
                    f"画用紙の向きを補正します: {turn_direction}, "
                    f"{turn_amount}度 (検出角={turn_deg:.1f}度)",
                    flush=True,
                )
                getattr(self, turn_direction)(turn_amount)
                self.single_fly_hover_flight(1)
                continue

            if confirm_before_move:
                answer = input(
                    "この移動を実行しますか？ [y=実行 / その他=中止]: "
                ).strip().lower()
                if answer != "y":
                    print("ユーザー確認により移動を中止しました", flush=True)
                    last_result["cancelled"] = True
                    return last_result

            self.single_fly_straight_flight(int(move_x*COLOR_MOVING_RATE),int(move_y*COLOR_MOVING_RATE),-10,20)
            self.single_fly_hover_flight(1)

        print(
            f"最大試行回数({max_iterations}回)に達しました。"
            "真上とは判定していません。",
            flush=True,
        )
        last_result["aligned"] = False
        last_result["success"] = False
        return last_result


def run_color_tuning(color="blue", camera_angle=None):
    """Hulaへ接続し、飛行させずに指定色のしきい値を調整する。"""
    api = ColorUserApi()
    if not api.connect():
        print("Hulaへの接続に失敗しました", flush=True)
        return None

    try:
        api.Plane_cmd_swith_rtp(0)
        api.single_fly_flip_rtp()
        time.sleep(3)
        if camera_angle is not None:
            api.Plane_cmd_camera_angle(1, camera_angle)
            time.sleep(2)
        return api.single_fly_color_tune(color)
    finally:
        try:
            api.Plane_cmd_swith_rtp(1)
        except Exception as error:
            print(f"映像ストリーム停止時にエラー: {error!r}", flush=True)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Hulaを飛行させずに色画用紙のHSVしきい値を調整します"
    )
    parser.add_argument(
        "color", nargs="?", choices=COLOR_RANGES, default="blue",
        help="調整する色 (default: blue)",
    )
    parser.add_argument(
        "--camera-angle", type=int,
        help="開始時に指定するジンバル角度。省略時は現在の角度を維持",
    )
    args = parser.parse_args()
    run_color_tuning(args.color, args.camera_angle)
