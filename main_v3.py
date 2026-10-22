import pyhula
import time
import math

import color_flight as color_flight
from color_flight import ColorUserApi

from ar_flight import ARUserApi

class ARColorUserApi(ARUserApi, ColorUserApi):
    pass

api = ARColorUserApi()

"""スタート地点を原点として、座標(cm)を設定する"""
map = {
    'start': [0,0],
    '0': [0,200],
    '1': [91,250],
    '2': [78,235],
    '7': [45,819],
    'blue': [75,1034],
}

"""順番を設定する。startは固定"""
order = ['start','2','7','blue']

"""看板と看板のある床のAR番号"""
"""orderやmapには床の方の値を入力"""
board_num = 8
floor_num = 7

"""色画用紙のときの入力座標と移動の差"""
COLOR_PAPER_ADJUSTMENT_X = 0
COLOR_PAPER_ADJUSTMENT_Y = -15

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

    #障害物検知ON
    api.single_fly_barrier_aircraft(True)

def takeoff(takeoff_height=100, Optical_flow_alignment=False, AR_number=0):
    """離陸(takeoff_height: 離陸後の高さ, Optical_flow_alignment: 光学フロー整列するかどうか)"""
    api.single_fly_lamplight(255, 255, 255, 3, 1) #離陸を知らせる白発光
    api.single_fly_takeoff() #離陸
    api.single_fly_straight_flight(0,0,takeoff_height-100,20) #離陸後の高さに移動

    #光学フロー整列
    if Optical_flow_alignment:
        ret = api.single_fly_Optical_flow_alignment(int(AR_number),20,0)
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

def move_and_land(num):

    print(f"move_and_land({num})")

    """一つ前がARならば、離陸後合わせる"""
    if order[num].isdecimal():
        if num != 1 and order[num-1].isdecimal():
            ret = takeoff(100,True,order[num-1])
        else:
            ret = takeoff(100,False)
    else:
        if num != 1 and order[num-1].isdecimal():
            ret = takeoff(120,True,order[num-1])
        else:
            ret = takeoff(120,False)
    if ret == "Fail":
        return "Fail"

    """ボード付きでないときは座標からヘリポート上に移動"""
    if order[num].isdecimal():
        if int(order[num]) != floor_num:
            api.single_fly_straight_flight(map[order[num]][0]-map[order[num-1]][0],map[order[num]][1]-map[order[num-1]][1],0,60,{'r':0,'g':255,'b':0,'mode':1})
    else:
        api.single_fly_straight_flight((map[order[num]][0]+COLOR_PAPER_ADJUSTMENT_X)-map[order[num-1]][0],(map[order[num]][1]+COLOR_PAPER_ADJUSTMENT_Y)-map[order[num-1]][1],0,60,{'r':0,'g':255,'b':0,'mode':1})
    if avoid_Barrier():
        return "found_Barrier"

    """ヘリポートに着陸"""

    if order[num].isdecimal():
        if int(order[num]) == floor_num:
            ret = ARBoard(board_num,floor_num,map[order[num]][0],map[order[num]][1])
            #if ret['comment'] == "床面光学フローに失敗":
            #    if find_AR(num) == "success":
            #        ret = api.single_fly_optical_flow_descent(30,2,int(order[num]),50)
            #    else:
            #        return "Fail"
        else:
            ret = api.single_fly_optical_flow_descent(30,2,int(order[num]),50)
            #if ret['success'] == False:
            #    if find_AR(num) == "success":
            #        ret = api.single_fly_optical_flow_descent(30,2,int(order[num]),50)
            #    else:
            #        return "Fail"
    else:
        ret = api.single_fly_color_overhead(order[num],2)

    print(ret)
    if ret['success'] == False:
        return "Fail"
    api.single_fly_touchdown()

    """最後でなければ10秒待機"""
    if num != len(order)-1:
        time.sleep(10)
    return "success"

def find_AR(num):
    """見つけられなかったARを探す"""
    MOVE_DISTANCE = 10
    last_moved_x = map[order[num]][0]-map[order[num-1]][0]
    last_moved_y = map[order[num]][1]-map[order[num-1]][1]
    last_moved = math.hypot(last_moved_x,last_moved_y)
    back_x = int(last_moved_x * MOVE_DISTANCE / last_moved)
    back_y = int(last_moved_y * MOVE_DISTANCE / last_moved)

    """来た道を{MOVE_DISTANCE}cm戻ってみる"""
    api.single_fly_straight_flight(back_x,back_y,0,MOVE_DISTANCE,{'r':255,'g':0,'b':255,'mode':1})
    if avoid_Barrier():
        return "found_Barrier"
    ret = api.single_fly_Optical_flow_recognition(int(order[num]),20)
    if ret['result']:
        return "success"
        
    """来た道を{MOVE_DISTANCE}cm進んでみる"""
    api.single_fly_straight_flight(back_x*-2,back_y*-2,0,MOVE_DISTANCE,{'r':255,'g':0,'b':255,'mode':1})
    if avoid_Barrier():
        return "found_Barrier"
    ret = api.single_fly_Optical_flow_recognition(int(order[num]),20)
    if ret['result']:
        return "success"

    """残り２方向を試す"""
    api.single_fly_straight_flight(-back_y+back_x,back_x+back_y,0,MOVE_DISTANCE,{'r':255,'g':0,'b':255,'mode':1})
    if avoid_Barrier():
        return "found_Barrier"
    ret = api.single_fly_Optical_flow_recognition(int(order[num]),20)
    if ret['result']:
        return "success"
    api.single_fly_straight_flight(2*back_y,-2*back_x,0,MOVE_DISTANCE,{'r':255,'g':0,'b':255,'mode':1})
    if avoid_Barrier():
        return "found_Barrier"
    ret = api.single_fly_Optical_flow_recognition(int(order[num]),20)
    if ret['result']:
        return "success"

    return "Fail"

def main():

    connect()

    for i in range(1,len(order),1):
        ret = move_and_land(i)
        if ret == "Fail":
            api.single_fly_touchdown()
            print(f"battery={api.get_battery()}")
            return "Fail"
        elif ret == "found_Barrier":
            print(f"battery={api.get_battery()}")
            return "found_Barrier"
    
    print(f"battery={api.get_battery()}")
    return "success"

PROGRAM_START_TIME = time.time()
print(main())
PROGRAM_END_TIME = time.time()
PROGRAM_TIME_SEC = int(PROGRAM_END_TIME - PROGRAM_START_TIME)
print(f"実行時間 : {int(PROGRAM_TIME_SEC/60)}m {PROGRAM_TIME_SEC%60}s")