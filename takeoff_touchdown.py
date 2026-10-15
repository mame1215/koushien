import pyhula
import time
import math

import color_flight
from color_flight import ColorUserApi

from ar_flight import ARUserApi

class ARColorUserApi(ARUserApi, ColorUserApi):
    pass

def avoid_Barrier():
    info = api.Plane_getBarrier()
    print(info)
    if info['forward']:
        api.single_fly_back(15,20,{'r':255,'g':0,'b':0,'mode':1})
        api.single_fly_touchdown()
        return True
    elif info['back']:
        api.single_fly_forward(15,20,{'r':255,'g':0,'b':0,'mode':1})
        api.single_fly_touchdown()
        return True
    elif info['left']:
        api.single_fly_right(15,20,{'r':255,'g':0,'b':0,'mode':1})
        api.single_fly_touchdown()
        return True
    elif info['right']:
        api.single_fly_left(15,20,{'r':255,'g':0,'b':0,'mode':1})
        api.single_fly_touchdown()
        return True
    else:
        return False

def flight(x,y,z,hover_time,mx,my,mz):
    start_time = time.time()
    start_position = api.get_coordinate()
    print(f"start_position = {start_position}")
    n = 0
    while time.time() - start_time < hover_time or n==0:
        position = api.get_coordinate()
        print(f"position = {position}")
        """dx = start_position[0] + x - position[0]
        dy = start_position[1] + y - position[1]
        dz = start_position[2] + z - position[2]
        l = math.hypot(dx,dy,dz)
        move_x = int(dx/l*10)
        move_y = int(dy/l*10)
        move_z = int(dz/l*10)
        print(f"move_x = {move_x}, move_y = {move_y}, move_z = {move_z}")
        api.single_fly_straight_flight(
            move_x,move_y,move_z, 20
            )"""

        dx = start_position[0] - mx*int(time.time()-start_time) + x - position[0]
        dy = start_position[1] - my*int(time.time()-start_time) + y - position[1]
        dz = start_position[2] - mz*int(time.time()-start_time) + z - position[2]
        print(f"move_x = {dx}, move_y = {dy}, move_z = {dz}")
        api.single_fly_straight_flight(dx,dy,dz,int(math.hypot(dx,dy,dz)*0.5),{'r':0,'g':255,'b':0,'mode':1})
        #api.single_fly_hover_flight(2,{'r':0,'g':0,'b':255,'mode':1})
        n += 1

        if avoid_Barrier():
            return "found_Barrier"
        
    """for i in range(3):
        position = api.get_coordinate()
        print(f"position = {position}")
        print(f"move_x = {-1*start_position[1]+x+position[1]}, move_y = {start_position[0]+y-position[0]}, move_z = {start_position[2]+z-position[2]}")
        api.single_fly_straight_flight(
            -1*start_position[1]+x+position[1], 
            start_position[0]+y-position[0], 
            start_position[2]+z-position[2], 20
            )"""
    position = api.get_coordinate()
    return {
        "input_x": x,
        "input_y": y,
        "input_z": z,
        "moved_x": position[0] - start_position[0],
        "moved_y": position[1] - start_position[1],
        "moved_z": position[2] - start_position[2],
        "expected_real_moved_x": mx*hover_time + position[0] - start_position[0],
        "expected_real_moved_y": my*hover_time + position[1] - start_position[1],
        "expected_real_moved_z": mz*hover_time + position[2] - start_position[2]
    }

def measure_gap():
    """滞空による誤差を調べる"""
    
    HOVER_TIME = 5 #誤差検証の滞空時間

    ret = api.single_fly_Optical_flow_alignment(0,20,0)
    if ret['result'] == False:
        print("Couldn't find AR")
        api.single_fly_touchdown()
        return "Fail"

    if avoid_Barrier():
        return "found_Barrier"

    start_position = api.get_coordinate()
    start_ar = api.single_fly_Optical_flow_recognition(0,20)
    print(f"start_position = {start_position}, start_ar = {start_ar}")

    #api.single_fly_hover_flight(HOVER_TIME,{'r':0,'g':0,'b':255,'mode':32})
    api.single_fly_straight_flight(10,10,10,5,{'r':0,'g':0,'b':255,'mode':32})
    time.sleep(0.5)
    api.single_fly_straight_flight(-10,-10,-10,5,{'r':0,'g':0,'b':255,'mode':32})

    end_position = api.get_coordinate()
    end_ar = api.single_fly_Optical_flow_recognition(0,20)
    print(f"end_position = {end_position}, end_ar = {end_ar}")

    mx = int((end_ar['x'] - start_ar['x'] - (end_position[0] - start_position[0]))/HOVER_TIME)
    my = int((end_ar['y'] - start_ar['y'] - (end_position[1] - start_position[1]))/HOVER_TIME)
    mz = int((end_ar['z'] - start_ar['z'] - (end_position[2] - start_position[2]))/HOVER_TIME)
    print(f"mx = {mx}, my = {my}, mz = {mz}")

    if avoid_Barrier():
        return "found_Barrier"

    ret = api.single_fly_Optical_flow_alignment(0,20,0)
    print(ret)

    return {
        "mx":mx,
        "my":my,
        "mz":mz,
        "result":ret['result']
    }

api = ARColorUserApi()

def main():
    if not api.connect():
        print("connect error")
    else:
        print("connection to station by wifi")

    print(f"battery={api.get_battery()}")

    api.Plane_cmd_swith_rtp(0)
    api.single_fly_flip_rtp()

    api.single_fly_camera_down()

    time.sleep(3)

    api.single_fly_barrier_aircraft(1)

    api.single_fly_lamplight(255, 255, 255, 3, 64)

    api.single_fly_takeoff()
    api.single_fly_up(20)

    ret = api.single_fly_Optical_flow_alignment(0,20,0)
    if ret['result'] == False:
        print("Couldn't find AR")
        api.single_fly_touchdown()
        return "Fail"

    """gap = measure_gap()
    if gap == "Fail":
        return "Fail"
    mx = gap['mx']
    my = gap['my']
    mz = gap['mz']

    #api.single_fly_straight_flight(30,0,0,30)

    #api.single_fly_hover_flight(2)

    #time.sleep(2)

    flight_ret = "None"
    if gap['result'] == True:
        #flight_ret = flight(160,175,0,10,mx,my,mz)"""
    api.single_fly_straight_flight(145,380,0,50,{'r':0,'g':255,'b':0,'mode':1})

    #print(f"flight_ret = {flight_ret}")
    ret = api.get_coordinate()
    print(ret)

    ret = api.single_fly_color_overhead("red")
    print(ret)

    api.single_fly_touchdown()
    return "success"

print(main())