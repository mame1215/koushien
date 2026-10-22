import pyhula
import time
import math

import color_flight as color_flight
from color_flight import ColorUserApi

from ar_flight import ARUserApi

class ARColorUserApi(ARUserApi, ColorUserApi):
    pass

def avoid_Barrier():
    #障害物検知ON
    #api.single_fly_barrier_aircraft(True)

    info = api.Plane_getBarrier()
    print(info)
    if info['forward']:
        api.single_fly_back(15,20,{'r':255,'g':0,'b':0,'mode':1})
        api.single_fly_touchdown()

        #障害物検知OFF
        #api.single_fly_barrier_aircraft(False)

        return True
    elif info['back']:
        api.single_fly_forward(15,20,{'r':255,'g':0,'b':0,'mode':1})
        api.single_fly_touchdown()

        #障害物検知OFF
        #api.single_fly_barrier_aircraft(False)

        return True
    elif info['left']:
        api.single_fly_right(15,20,{'r':255,'g':0,'b':0,'mode':1})
        api.single_fly_touchdown()

        #障害物検知OFF
        #api.single_fly_barrier_aircraft(False)

        return True
    elif info['right']:
        api.single_fly_left(15,20,{'r':255,'g':0,'b':0,'mode':1})
        api.single_fly_touchdown()

        #障害物検知OFF
        #api.single_fly_barrier_aircraft(False)

        return True
    else:
        #障害物検知OFF
        #api.single_fly_barrier_aircraft(False)

        return False


def ARBoard(board_AR_number,floor_AR_number,board_x,board_y):
    api.Plane_cmd_camera_angle(0,0)
    
    angle = int(math.degrees(math.atan2(board_x,board_y)))
    if angle > 0:
        api.single_fly_turnright(angle)
    else:
        api.single_fly_turnleft(-angle)

    api.single_fly_hover_flight(3)

    ret = api.single_fly_Anticipatory_recognition(board_AR_number)

    if ret['result'] == True:
        api.single_fly_straight_flight(ret['x'],ret['y']-40,0,60)
        if avoid_Barrier():
            return {
                'success' : False,
                'comment' : "found_Barrier"
            }

        api.Plane_cmd_camera_angle(1,90)

        api.single_fly_hover_flight(5)

        if not api.single_fly_optical_flow_descent(20,2,floor_AR_number,50)['success']:
            return {
                'success' : False,
                'comment' : "床面光学フロー整列に失敗"
            }
        return {
            'success' : True,
            'comment' : "success"
        }
    else:
        return {
            'success' : False,
            'comment' : "ボード検出失敗"
        }


api = ARColorUserApi()
if not api.connect():
    print("connect error")
else:
    print("connection to station by wifi")

print(f"battery={api.get_battery()}")

api.single_fly_takeoff()

time.sleep(5)

api.single_fly_touchdown()
