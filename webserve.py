import network
import socket
import time
import json
import ntptime
from machine import Pin, I2C, RTC
import uasyncio as asyncio
import timeclarkconfig as cfg
from ssd1306 import SSD1306_I2C

# Set up the screen.
i2c=I2C(0,sda=Pin(0), scl=Pin(1), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)

oled.fill(0)
oled.text("The TimeClark", 0, 0)
oled.text("Setting up...", 0, 20)
oled.show()

onboard = Pin("LED", Pin.OUT, value=0)
button = Pin(16, Pin.IN, Pin.PULL_DOWN)

ssid = cfg.ssid
password = cfg.password

html_file = open("template.html", "r")
html = html_file.read()
html_file.close()

css_file = open("template.css", "r")
css_contents = css_file.read()
css_file.close()

wlan = network.WLAN(network.STA_IF)

# boolean - true = working, false=not
current_work_state = False
clark_in_time = 0

def connect_to_network():
    wlan.active(True)
    wlan.config(pm = 0xa11140)  # Disable power-save mode
    wlan.connect(ssid, password)

    max_wait = 20
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        print('waiting for connection...')
        time.sleep(1)

    if wlan.status() != 3:
        raise RuntimeError('network connection failed')
    else:
        print('connected')
        status = wlan.ifconfig()
        print('ip = ' + status[0])
        
        oled.fill(0)
        oled.text("The TimeClark", 0, 0)
        oled.text("ip address: ", 0, 20)
        oled.text(status[0], 0, 40)
        oled.show()

        print("Current time: " + str(time.localtime()))
        ntptime.settime()
        print("Set time thru ntp: " + str(time.localtime()))
        UTC_OFFSET = -5 * 60 * 60
        print("UTC_OFFSET = " + str(UTC_OFFSET))
        actual_time = time.localtime(time.time() + UTC_OFFSET)
        #actual_time = machine.RTC().datetime() + UTC_OFFSET
        print(type(actual_time))
        print(actual_time)
        
        #datetime() produces a tuple of year, month, day, dotw, hour, minute, second, ?

        machine.RTC().datetime((actual_time[0], actual_time[1], actual_time[2], actual_time[6], actual_time[3], actual_time[4], actual_time[5], 0))
        #rtc.init(actual_time)
        #rtc.datetime(actual_time)
        print(str(machine.RTC().datetime()))
        #machine.RTC.init(actual_time)
        print("Adjusted time: " + str(time.localtime()))



def add_data_to_file(json_string):
    print("WRITING TO FILE!")
    db = open("testdata.txt","a")
    print("Json in add_data: " + json_string)
    db.write(json_string + "\n")
    db.flush()
    db.close()



def getISOTimeStringRightNow():
    dt = time.localtime()
        
    dt_iso8601 = str(dt[0]) + "-" + f'{dt[1]:02d}' + "-" + f'{dt[2]:02d}' + "T" + \
                        f'{dt[3]:02d}' + ":" + f'{dt[4]:02d}' + ":" + f'{dt[5]:02d}' + "-05:00"
    
    return dt_iso8601



async def serve_client(reader, writer):
    global current_work_state, clark_in_time
    
    print("Client connected")
    request_line = await reader.readline()
    print("Request:", request_line)
    # We are not interested in HTTP request headers, skip them
    while await reader.readline() != b"\r\n":
        pass

    request = str(request_line)
    
    #print(request.find('/buttonpress'))
    
    if (request.find('/heartbeat') != -1):
        print("Doing /heartbeat")
        data = {}
        data['work_state'] = current_work_state
        if (current_work_state == True):
            data['when'] = clark_in_time
        else:
            data['when'] = getISOTimeStringRightNow()
        
        json_data = json.dumps(data)
        print("Hearbeat sending back:  " + json_data)

        writer.write('HTTP/1.0 200 OK\r\nContent-type:application/json\r\n\r\n')
        writer.write(json_data)
        await writer.drain()
        await writer.wait_closed()
        print("Client disconnected")
        return



    if (request.find('/buttonpress') != -1):
        print("Doing /buttonpress")

        #rtc = machine.RTC()
        #rtc_time = rtc.datetime()
        #print("rtc_time: " + str(rtc_time))

        current_work_state = not current_work_state
        onboard.value(current_work_state)
        data = {}
        data['work_state'] = current_work_state
        
        dt = time.localtime()
        
        dt_iso8601 = str(dt[0]) + "-" + f'{dt[1]:02d}' + "-" + f'{dt[2]:02d}' + "T" + \
                        f'{dt[3]:02d}' + ":" + f'{dt[4]:02d}' + ":" + f'{dt[5]:02d}' + "-05:00"

        #dt = rtc.datetime()

        print(dt)
        print (dt_iso8601)
        
        data['when'] = dt_iso8601
        clark_in_time = dt_iso8601
        
        print(data)
        print("Timestamp info: ")
        json_data = json.dumps(data)
        print(json_data)

        add_data_to_file(json_data)

        response = json_data
        writer.write('HTTP/1.0 200 OK\r\nContent-type:application/json\r\n\r\n')
        writer.write(response)
        await writer.drain()
        await writer.wait_closed()
        print("Client disconnected")
        return
        
      
    
    if (request.find("/template.css") != -1):
        print("Loading template.css")
        #css_file = open("template.css", "r")
        #css_contents = css_file.read()
        writer.write('HTTP/1.0 200 OK\r\nContent-type:text/css\r\n\r\n')
        writer.write(css_contents)
        await writer.drain()
        await writer.wait_closed()
        print("Client disconnected")
        return


    led_on = request.find('/light/on')
    led_off = request.find('/light/off')
    print( 'led on = ' + str(led_on))
    print( 'led off = ' + str(led_off))

    stateis = ""
    if led_on == 6:
        print("led on")
        led.value(1)
        onboard.value(1)
        stateis = "LED is ON"
    
    if led_off == 6:
        print("led off")
        led.value(0)
        onboard.value(0)
        stateis = "LED is OFF"
        
    #response = html % stateis
    response = html
    writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    writer.write(response)

    await writer.drain()
    await writer.wait_closed()
    print("Client disconnected")



def hardware_button_pressed():
    global current_work_state, clark_in_time

    print("Hardware button pressed!")
    current_work_state = not current_work_state
    onboard.value(current_work_state)

    dt_ISO = getISOTimeStringRightNow()

    if (current_work_state == False):
        clark_in_time = 0
    else:
        clark_in_time = dt_ISO

    data = {}
    data['work_state'] = current_work_state
    #dt = time.localtime()
    #dt_iso8601 = str(dt[0]) + "-" + f'{dt[1]:02d}' + "-" + f'{dt[2]:02d}' + "T" + \
    #             f'{dt[3]:02d}' + ":" + f'{dt[4]:02d}' + ":" + f'{dt[5]:02d}' + "-05:00"
    #print("dt:")
    #print(dt)
    #print (dt_iso8601)
        
    data['when'] = dt_ISO
    print(data)
    print("Timestamp info: ")
    json_data = json.dumps(data)
    print(json_data)

    add_data_to_file(json_data)




async def main():
    print('Connecting to Network...')
    connect_to_network()

    print('Setting up webserver...')
    asyncio.create_task(asyncio.start_server(serve_client, "0.0.0.0", 80))
    while True:
        if button.value():
            hardware_button_pressed()
            await asyncio.sleep(.5)
        else:
            await asyncio.sleep(.1)
  
try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()
    

    
        
        
    
    
    