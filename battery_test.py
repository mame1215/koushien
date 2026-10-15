import pyhula
import time

api = pyhula.UserApi()

if not api.connect():
    print("connect error")
else:
    print("connection to station by wifi")

print(f"battery={api.get_battery()}")