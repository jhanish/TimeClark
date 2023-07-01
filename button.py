from machine import Pin
import time

button = Pin(16, Pin.IN, Pin.PULL_DOWN)

while True:
    if button.value():
        print("Button pressed...")
        time.sleep(0.5)

