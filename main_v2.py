import pyhula
import time
import math

import color_flight
from color_flight import ColorUserApi

from ar_flight import ARUserApi

class ARColorUserApi(ARUserApi, ColorUserApi):
    pass

def avoid_Barrier():
    #障害物検知ON
    api.single_fly_barrier_aircraft(True)

    info = api.Plane_getBarrier()
    print(info)
    if info['forward']:
        api.single_fly_back(15,20,{'r':255,'g':0,'b':0,'mode':1})
        api.single_fly_touchdown()

        #障害物検知OFF
        api.single_fly_barrier_aircraft(False)

        return True
    elif info['back']:
        api.single_fly_forward(15,20,{'r':255,'g':0,'b':0,'mode':1})
        api.single_fly_touchdown()

        #障害物検知OFF
        api.single_fly_barrier_aircraft(False)

        return True
    elif info['left']:
        api.single_fly_right(15,20,{'r':255,'g':0,'b':0,'mode':1})
        api.single_fly_touchdown()

        #障害物検知OFF
        api.single_fly_barrier_aircraft(False)

        return True
    elif info['right']:
        api.single_fly_left(15,20,{'r':255,'g':0,'b':0,'mode':1})
        api.single_fly_touchdown()

        #障害物検知OFF
        api.single_fly_barrier_aircraft(False)

        return True
    else:
        #障害物検知OFF
        api.single_fly_barrier_aircraft(False)

        return False

def connect():
    """Hulaに接続・初期化(引数なし)"""

    if not api.connect():
        print("connect error")
    else:
        print("connection to station by wifi")

    #バッテリー残量
    print(f"battery={api.get_battery()}")

    #映像取得
    api.Plane_cmd_swith_rtp(0)
    api.single_fly_flip_rtp()

    #カメラ90度下
    api.single_fly_camera_down()

    #映像取得待機
    time.sleep(3)

    #障害物検知OFF
    api.single_fly_barrier_aircraft(False)

def takeoff(takeoff_height=100, Optical_flow_alignment=False, AR_number=0):
    """離陸(takeoff_height: 離陸後の高さ, Optical_flow_alignment: 光学フロー整列するかどうか)"""
    api.single_fly_lamplight(255, 255, 255, 3, 1) #離陸を知らせる白発光
    api.single_fly_takeoff() #離陸
    api.single_fly_straight_flight(0,0,takeoff_height-100,20) #離陸後の高さに移動

    #光学フロー整列
    if Optical_flow_alignment:
        ret = api.single_fly_Optical_flow_alignment(AR_number,20,0)
        if ret['result'] == False:
            print("Couldn't find AR")
            api.single_fly_touchdown()
            return "Fail"
        
    return "success"

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
        api.single_fly_straight_flight(ret['x']-10,ret['y']-40,0,60)
        if avoid_Barrier():
            return "found_Barrier"

        api.Plane_cmd_camera_angle(1,90)

        api.single_fly_hover_flight(5)

        if not api.single_fly_optical_flow_descent(20,2,floor_AR_number,50)['success']:
            return "床面光学フロー整列に失敗"
        return "success"
    else:
        return "ボード検出失敗"



api = ARColorUserApi()

def main():

    connect()

    """No.0に着陸"""
    ret = takeoff(100,False)
    if ret == "Fail":
        return "Fail"

    api.single_fly_straight_flight(-65,100,0,60,{'r':0,'g':255,'b':0,'mode':1})
    if avoid_Barrier():
        return "found_Barrier"

    ret = api.single_fly_optical_flow_descent(30,2,0,50)
    print(ret)
    api.single_fly_touchdown()
    if ret['success'] == False:
        return "Fail"


    time.sleep(10)

    """No.1に着陸"""
    ret = takeoff(100,True,0)
    if ret == "Fail":
        return "Fail"

    api.single_fly_straight_flight(-15,145,0,60,{'r':0,'g':255,'b':0,'mode':1})
    if avoid_Barrier():
        return "found_Barrier"

    ret = api.single_fly_optical_flow_descent(30,2,1,50)
    print(ret)
    api.single_fly_touchdown()
    if ret['success'] == False:
        return "Fail"

    time.sleep(10)

    """ボード付きに着陸"""
    ret = takeoff(100,True,1)
    if ret == "Fail":
        return "Fail"

    ret = ARBoard(2,3,120,240)
    print(ret)
    if not ret == "success":
        api.single_fly_touchdown()
        return "ARBoard Fail"

    print("ARBoard success")
    api.single_fly_touchdown()

    time.sleep(10)

    """緑画用紙に着陸"""
    ret = takeoff(120,True,3)
    if ret == "Fail":
        return "Fail"

    api.single_fly_straight_flight(-120+15,-240,0,60,{'r':0,'g':255,'b':0,'mode':1})
    if avoid_Barrier():
        return "found_Barrier"    

    ret = api.single_fly_color_overhead("green",2)
    print(ret)

    if avoid_Barrier():
        return "found_Barrier"

    api.single_fly_touchdown()
    print(f"battery={api.get_battery()}")
    return "success"

PROGRAM_START_TIME = time.time()
print(main())
PROGRAM_END_TIME = time.time()
PROGRAM_TIME_SEC = int(PROGRAM_END_TIME - PROGRAM_START_TIME)
print(f"実行時間 : {int(PROGRAM_TIME_SEC/60)}m {PROGRAM_TIME_SEC%60}s")