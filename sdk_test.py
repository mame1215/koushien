"""Simplest possible example: connect, take off, land.

Matches the canonical example from HighGreat's own docs, using hula_sdk
instead of talking to pyhula directly -- pyhula's raw connect() doesn't
work on Windows without the patches this wraps (see README).

Needs clear space -- it actually takes off.

Requires `venv\\Scripts\\python.exe -m pip install -e .` once, from the
repo root.
"""
from hula_sdk import HulaDrone

DRONE_IP = "192.168.100.1"

with HulaDrone(DRONE_IP) as drone:
    print("plane id:", drone.plane_id())
    print("battery:", drone.battery())
    drone.takeoff()
    drone.land()