import math

import pyhula

class ARUserApi(pyhula.UserApi):
    def single_fly_ar_detect(self, ar_number=0):
        """ARマーカーを認識し、検出位置を返す。機体は動かさない。"""
        frame = self.get_image_array()
        result = {
            "success": False,
            "aligned": False,
            "AR_number": ar_number,
            "move_x_cm": 0.0,
            "move_y_cm": 0.0,
            "move_z_cm": 0.0,
            "turn_deg": 0.0,
        }
        if frame is None or not hasattr(frame, "shape") or len(frame.shape) != 3:
            print(f"AR認識失敗: {ar_number}, 映像フレームなし", flush=True)
            return result

        detection = self.single_fly_Anticipatory_recognition(ar_number)
        if (
            not isinstance(detection, dict)
            or not detection.get("result", False)
        ):
            print(f"AR認識失敗: {ar_number}", flush=True)
            return result

        move_x = float(detection.get("x", 0.0))
        move_y = float(detection.get("y", 0.0))
        move_z = float(detection.get("z", 0.0))
        turn_deg = float(detection.get("angle", 0.0))
        result.update(
            {
                "success": True,
                "move_x_cm": move_x,
                "move_y_cm": move_y,
                "move_z_cm": move_z,
                "turn_deg": turn_deg,
                "raw": detection,
            }
        )
        print(
            f"AR認識成功: AR番号={ar_number}, "
            f"x={move_x:.1f}, y={move_y:.1f}, z={move_z:.1f}, "
            f"角度={turn_deg:.1f}度",
            flush=True,
        )
        return result

    def single_fly_optical_flow_descent(
        self,
        target_height_cm=20,
        alignment_count=3,
        qr_id=0,
        max_step_cm=10,
    ):
        """現在高度から目標高度まで分割下降し、各段階で位置を整列する。"""
        if target_height_cm < 0:
            raise ValueError("target_height_cm must be non-negative")
        if alignment_count < 1:
            raise ValueError("alignment_count must be at least 1")
        if max_step_cm < 1:
            raise ValueError("max_step_cm must be at least 1")

        current_height_cm = float(self.get_plane_distance())
        if not math.isfinite(current_height_cm) or current_height_cm < 0:
            raise ValueError("plane height must be a finite non-negative number")

        if not self.single_fly_Optical_flow_alignment(qr_id, 20, 0)['result']:
            print("下降前のQR光学フロー整列に失敗しました", flush=True)
            return {
                "success": False,
                "aligned": False,
                "qr_id": qr_id,
                "start_height_cm": current_height_cm,
                "target_height_cm": target_height_cm,
                "descent_cm": 0,
            }

        descent_cm = max(0, int(round(current_height_cm - target_height_cm)))
        segment_count = min(
            descent_cm,
            max(alignment_count, (descent_cm + max_step_cm - 1) // max_step_cm),
        )
        if segment_count == 0:
            return {
                "success": True,
                "aligned": True,
                "qr_id": qr_id,
                "start_height_cm": current_height_cm,
                "target_height_cm": target_height_cm,
                "descent_cm": 0,
            }

        base_descent_cm, extra_cm = divmod(descent_cm, segment_count)
        for segment in range(segment_count):
            step_cm = base_descent_cm + (1 if segment < extra_cm else 0)
            self.single_fly_down(step_cm)
            print(f"QR光学フロー整列 : {segment + 1}/{segment_count}回目")
            if not self.single_fly_Optical_flow_alignment(qr_id, 20, 0)['result']:
                print(
                    f"下降後のQR光学フロー整列に失敗しました: "
                    f"{segment + 1}/{segment_count}回",
                    flush=True,
                )
                return {
                    "success": False,
                    "aligned": False,
                    "qr_id": qr_id,
                    "start_height_cm": current_height_cm,
                    "target_height_cm": target_height_cm,
                    "descent_cm": base_descent_cm * (segment + 1)
                    + min(segment + 1, extra_cm),
                }

        return {
            "success": True,
            "aligned": True,
            "qr_id": qr_id,
            "start_height_cm": current_height_cm,
            "target_height_cm": target_height_cm,
            "descent_cm": descent_cm,
        }

if __name__ == "__main__":
    print("ARUserApiをimportして使用してください")
        