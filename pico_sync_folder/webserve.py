import network
import socket
import time
import json
import ntptime
from machine import Pin, I2C, RTC
import uasyncio as asyncio
import timeclarkconfig as cfg
from ssd1306 import SSD1306_I2C
import gc
import os
import machine 
#import _thread
import math
from tinydb import TinyDB, Query

#Set up the database
tcdb = TinyDB('timeclarkdb.json')

# Set up the screen.
i2c=I2C(0,sda=Pin(0), scl=Pin(1), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)
current_mini_screen = 1
mini_screens_count = 3

oled.fill(0)
oled.text("The TimeClark", 0, 0)
oled.text("Setting up...", 0, 20)
oled.show()

def displayRefresh():
    refreshMiniScreen()
    #threading.Timer(1.0, displayRefresh).start()

onboard = Pin("LED", Pin.OUT, value=0)
button = Pin(16, Pin.IN, Pin.PULL_DOWN)
button_left = Pin(26, Pin.IN, Pin.PULL_DOWN)
button_right = Pin(27, Pin.IN, Pin.PULL_DOWN)

ssid = cfg.ssid
password = cfg.password
tz_offset = cfg.timezone_offset

html_file = open("template.html", "r")
html = html_file.read()
html_file.close()

css_file = open("template.css", "r")
css_contents = css_file.read()
css_file.close()

ip_address = "Unobtained"

wlan = network.WLAN(network.STA_IF)

# boolean - true = working, false=not
current_work_state = False
# when clarked in, in iso string format
clark_in_time = 0
clark_in_time_in_seconds = 0
clean_time_string = ""

def connect_to_network():
    global ip_address

    wlan.active(True)
    wlan.config(pm = 0xa11140)  # Disable power-save mode
    wlan.connect(ssid, password)

    max_wait = 30
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
        ip_address = status[0]
        
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

        # Set the clock time, with our utc_offset applied.
        machine.RTC().datetime((actual_time[0], actual_time[1], actual_time[2], actual_time[6], actual_time[3], actual_time[4], actual_time[5], 0))
        #rtc.init(actual_time)
        #rtc.datetime(actual_time)
        print(str(machine.RTC().datetime()))
        #machine.RTC.init(actual_time)
        print("Adjusted time: " + str(time.localtime()))



def isFile(filename):
    found = False

    try:
        f = open(filename, "br")
        f.close()
        found = True
    except:
        found = False

    return found



def add_data_to_file(in_or_out, tstamp):
    
    in_or_out_string = 'i'
    if (in_or_out == False):
        in_or_out_string = "o"
    
    print("WRITING TO FILE!")
    db = open("testdata.txt","a")
    print("Adding_data: " + str(in_or_out) + " : " + tstamp)
    db.write(in_or_out_string + "," + tstamp + "\n")
    db.flush()
    db.close()

    tcdb.insert({'in_or_out': in_or_out_string, 'tstamp': tstamp})

#{"work_state": false, "when": "2023-06-28T20:57:06-05:00"}
#def add_record_to_save_file(ClarkInOutEvent cioe):

def getISOTimeStringRightNow():
    return getISOTimeString(time.localtime())

def getISOTimeString(time_tuple):
    dt = time_tuple
        
    dt_iso8601 = str(dt[0]) + "-" + f'{dt[1]:02d}' + "-" + f'{dt[2]:02d}' + "T" + \
                        f'{dt[3]:02d}' + ":" + f'{dt[4]:02d}' + ":" + f'{dt[5]:02d}' + "-05:00"
    
    clean_time_string = f'{dt[0]}{dt[1]:02d}{dt[2]:02d}{dt[3]:02d}{dt[4]:02d}{dt[5]:02d}'
    
    return dt_iso8601, clean_time_string



def getFormattedStringFromStamp(tstamp):
    tm = time.localtime(tstamp)    
    ampm = "am"
    the_hour = tm[3]
    if the_hour > 12:
        ampm = "pm"
        the_hour = the_hour - 12
    if the_hour == 0:
        the_hour = 12

    return f"{the_hour:02}:{tm[4]:02}:{tm[5]:02}{ampm}" 



def getCurrentTimeShortString():
    return getFormattedStringFromStamp(time.time())



def getClarkedInDuration():
    
    global clark_in_time_in_seconds

    time_now = time.mktime(time.localtime())
    time_passed = time_now - clark_in_time_in_seconds
    #print(f"Time passed: {time_passed}")

    days = math.floor(time_passed / (60 * 60 * 24))
    if (days > 0):
        time_passed = time_passed - (days * (60 * 60 * 24))

    hours = math.floor(time_passed / (60 * 60))
    if (hours > 0):
        time_passed = time_passed - (hours * (60 * 60))

    minutes = math.floor(time_passed / 60)
    if (minutes > 0):
        time_passed = time_passed - (minutes * 60)

    seconds = time_passed

    return (days, hours, minutes, seconds)



def getLogJSON():
    log_line_list = []
    file = open('testdata.txt', 'r')

    while True:
        data = {}
        line = file.readline()

        if not line:
            break
        print(line)
        line_data = line.split(",")
        if (line_data[0] == "i"):
            data['work_state'] = True
        else:
            data['work_state'] = False    

        data['when'] = int(line_data[1])
        log_line_list.append(data)

        ##year = line_data[1][0:3]
        ##month = line_data[1][4:5]
        ##day = line_data[1][6:7]
        ##hour = line_data[1][8:9]
        ##minute = line_data[1][10:11]
        ##second = line_data[1][12:13]
    
    log_line_list.reverse()
    json_data = json.dumps(log_line_list)
    file.close()

    print("RETURNING THIS JSON DATA: " + json_data)

    return json_data



async def serve_client(reader, writer):
    global current_work_state, clark_in_time
    
    print("Client connected")
    request_line = await reader.readline()
    print("Request:", request_line)
    # We are not interested in HTTP request headers, skip them
    while await reader.readline() != b"\r\n":
        pass

    request = str(request_line)
    
    clean_str = ""

    if (request.find('/heartbeat') != -1):
        print("Doing /heartbeat")
        data = {}
        data['work_state'] = current_work_state
        if (current_work_state == True):
            data['when'] = clark_in_time
        else:
            iso_str, clean_str = getISOTimeStringRightNow()
            data['when'] = iso_str
        
        json_data = json.dumps(data)
        print("Hearbeat sending back:  " + json_data)

        writer.write('HTTP/1.0 200 OK\r\nContent-type:application/json\r\n\r\n')
        writer.write(json_data)
        await writer.drain()
        await writer.wait_closed()
        print("Returned results for /heartbeat...")
        return

    #req.open("GET", "http://" + location.hostname + "/timediff?timestamp=" + tstamp
    if (request.find('/timediff') != -1):
        #current_time = time.mktime(time.localtime())
        current_time = time.time()
        print("ACTUAL TIME: " + getCurrentTimeShortString())
        print("CURRENT TIME: " + getFormattedStringFromStamp(current_time))
        client_tstamp = int(request.split("timestamp=")[1].split(" ")[0]) + (tz_offset * 60 * 60)
        print("CLIENT TIME: " + getFormattedStringFromStamp(client_tstamp))
        diff = current_time - client_tstamp
        print("DIFF: " + str(diff))
        writer.write('HTTP/1.0 200 OK\r\nContent-type:text/plain\r\n\r\n')
        writer.write(str(diff))
        await writer.drain()
        await writer.wait_closed()
        print("Returned results for /timediff...")
        return
                
    

    if (request.find('/log') != -1):
        json_log = getLogJSON()
        writer.write('HTTP/1.0 200OK\r\nContent-type:application/json\r\n\r\n')
        writer.write(json_log)
        await writer.drain()
        await writer.wait_closed()
        return


    if (request.find('/images/') != -1):
        print("LOOKING FOR SOMETHING IN IMAGES FOLDER!")
        print(request)

        pieces = request.split('/images/')
        pieces2 = pieces[-1].split(' HTTP/1')
        filename = "images/" + pieces2[0]
        print("Filename: " + filename)


        if (isFile(filename) == True):
            writer.write('HTTP/1.0 200OK\r\nContent-type:image/png\r\n\r\n')
            image_file = open(filename, "rb")
            image_contents = image_file.read()  
            writer.write(image_contents)
            await writer.drain()
            await writer.wait_closed()
            print("Delivered image: " + filename)
        else:
            ### NO MATCHES, SEND 404 ###
            writer.write('HTTP/1.0 404 Not Found\r\nContent-Type: text/plain\r\n\r\n')
            await writer.drain()
            await writer.wait_closed()
            print("Could not find the requested image.")
            print("Delivered 404 error for the following request...")
            print(request_line)

        return


    if (request.find('/buttonpress') != -1):
        global clark_in_time
        
        print("Doing /buttonpress")

        hardware_button_pressed()

        data = {}
        data['work_state'] = current_work_state
        data['when'] = clark_in_time
        
        print(data)
        print("Timestamp info: ")
        json_data = json.dumps(data)
        print(json_data)

        response = json_data
        writer.write('HTTP/1.0 200 OK\r\nContent-Type:application/json\r\n\r\n')
        writer.write(response)
        await writer.drain()
        await writer.wait_closed()
        print("Returned results for /buttonpress...")
        return
        
    if (request.find("digital-7%20(italic).ttf") != -1):
        # client is requesting the font.
        font_file = open("digital-7 (italic).ttf", "rb")
        font_contents = font_file.read()  
        writer.write('HTTP/1.0 200 OK\r\nContent-Type:font/ttf\r\n\r\n')
        writer.write(font_contents)
        await writer.drain()
        await writer.wait_closed()
        print("Delivered digital-7 font file")
        font_file.close()
        return
    
    if (request.find("/template.css") != -1):
        global css_contents

        print("Loading template.css")
        #css_file = open("template.css", "r")
        #css_contents = css_file.read()
        writer.write('HTTP/1.0 200 OK\r\nContent-Type:text/css\r\n\r\n')
        writer.write(css_contents)
        await writer.drain()
        await writer.wait_closed()
        print("Delivered template.css")
        return

    if (request.find(" / ") != -1) : 
        global html

        #response = html % stateis
        response = html
        #writer.write('HTTP/1.0 404 Not Found\r\n\r\n')
        writer.write('HTTP/1.0 200 OK\r\nContent-Type:text/html\r\n\r\n')
        writer.write(response)

        await writer.drain()
        await writer.wait_closed()
        print("Delivered / (default document)")
        return
    
    ### NO MATCHES, SEND 404 ###
    writer.write('HTTP/1.0 404 Not Found\r\nContent-Type: text/plain\r\n\r\n')
    await writer.drain()
    await writer.wait_closed()
    print("Delivered 404 error for the following request...")
    print(request_line)



def hardware_button_pressed():
    global current_work_state, clark_in_time, clark_in_time_in_seconds, current_mini_screen

    print("Hardware button pressed!")
    current_work_state = not current_work_state
    onboard.value(current_work_state)

    ltime = time.localtime()
    dt_epoch = time.mktime(ltime)
    clark_in_time_in_seconds = dt_epoch
    dt_ISO, dt_clean = getISOTimeStringRightNow()

    if (current_work_state == False):
        clark_in_time = 0
    else:
        clark_in_time = dt_ISO

    data = {}
    data['work_state'] = current_work_state
    data['when'] = dt_ISO
    json_data = json.dumps(data)

    add_data_to_file(data['work_state'], dt_clean)
    
    current_mini_screen = 3    
    refreshMiniScreen()

def button_left_pressed():
    global current_mini_screen

    current_mini_screen = current_mini_screen - 1
    if (current_mini_screen < 1):
        current_mini_screen = mini_screens_count
    refreshMiniScreen()

def button_right_pressed():
    global current_mini_screen

    current_mini_screen = current_mini_screen + 1
    if (current_mini_screen > mini_screens_count):
        current_mini_screen = 1
    refreshMiniScreen()






def fillToMakeCentered(str):
    spaces = math.floor((16 - len(str)) / 2)
    return ' ' * int(spaces) + str

def refreshMiniScreen():
    global ip_address, current_work_state, clark_in_time

    oled.fill(0)

    # THE DEFAULT PAGE
    if current_mini_screen == 1:

        time_string = getCurrentTimeShortString()

        oled.text(" THE TIMECLARK", 0, 0)
        oled.text(f"   {time_string}", 0, 16)
        oled.text("***************************", 0, 27)
        oled.text("  IP Address", 0, 38)
        oled.text(fillToMakeCentered(ip_address), 0, 48)
        

    # INFO SCREEN
    if current_mini_screen == 2:
        oled.text(f"INFO", 0, 0)
        s = os.statvfs('/')
        oled.text(f"Free:{s[0]*s[3]/1024} KB", 0, 18)
        oled.text(f"Mem: {gc.mem_alloc()} of", 0, 27)
        oled.text(f"     {gc.mem_free()} bytes used.", 0, 36)
        oled.text(f"CPU: {machine.freq()/1000000}Mhz", 0, 47)
        oled.text(f"IP:  {ip_address}", 0, 56)

    # THE STATUS PAGE
    if current_mini_screen == 3:
        if (current_work_state == True):
            
            x = getClarkedInDuration()
            
            oled.text("CLARKED IN", 0, 0)
            clark_in_time_info = getTupleFromISODate(clark_in_time)
            time_in_string = f"{clark_in_time_info[1]}/{clark_in_time_info[2]}/{clark_in_time_info[0]}"
            time_in_string2 = f"{clark_in_time_info[3]}:{clark_in_time_info[4]}:{clark_in_time_info[5]} {clark_in_time_info[6]}"
            oled.text(time_in_string, 0, 18)
            oled.text(time_in_string2, 0, 27)
            oled.text(getCurrentTimeShortString(), 0, 45)
            oled.text(f"{x[0]}d:{x[1]}h:{x[2]}m:{x[3]}s", 0, 54)

        else:
            oled.text("CLARKED OUT", 0, 0)
            oled.text(getCurrentTimeShortString(), 0, 45)

    oled.show()

def getTupleFromISODate(whenString):
    timeanddate = whenString.split('T')
    date_parts = timeanddate[0].split('-')
    time_parts = timeanddate[1][0:8].split(':')
    time_zone = timeanddate[1][8:]
    return (date_parts[0], date_parts[1], date_parts[2], time_parts[0], time_parts[1], time_parts[2], time_zone)

async def everySecondMaintenance():
    while True:
        #print("***** INSIDE everySecondMaintenance!!")
        refreshMiniScreen()
        await asyncio.sleep(1)

def loadLastState():
    global current_work_state, clark_in_time, clark_in_time_in_seconds, current_mini_screen
    lastline = ""

    with open('testdata.txt') as f:
        for line in f:
            pass
            lastline = line
        
    last_data = lastline.split(',')

    
    if (last_data[0] == 'i'):
    # The TimeClark is still running...  set it up to continue.
        onboard.value(True)
        clark_in_time = convertEZDateToISOString(last_data[1])
        clark_in_time_in_seconds = convertEZDateToEpoch(last_data[1])
        current_work_state = True
        
        current_mini_screen = 3
        refreshMiniScreen()
    return

def convertEZDateToTuple(ezdate):
    year = int(ezdate[0:4])
    month = int(ezdate[4:6])
    day = int(ezdate[6:8])
    hour = int(ezdate[8:10])
    minute = int(ezdate[10:12])
    second = int(ezdate[12:14])
    return (year, month, day, hour, minute, second)

def convertEZDateToEpoch(ezdate):
    tup_date = convertEZDateToTuple(ezdate)
    return time.mktime((tup_date[0], tup_date[1], tup_date[2], tup_date[3], tup_date[4], tup_date[5], 0, 0))

def convertEZDateToISOString(ezdate):
    tup_date = convertEZDateToTuple(ezdate)
    tup_date_iso8601 = str(tup_date[0]) + "-" + f'{tup_date[1]:02d}' + "-" + f'{tup_date[2]:02d}' + "T" + \
                        f'{tup_date[3]:02d}' + ":" + f'{tup_date[4]:02d}' + ":" + f'{tup_date[5]:02d}' + "-05:00"
    return tup_date_iso8601
    
def assureSaveFile():
    print("Assuring save file existence...")
    try:
        with open('testdata.txt') as file:
          file.close()
          print("File found.")
          return
    except OSError:
        print("File not found.  Creating.")
        with open('testdata.txt', 'w') as file:
            file.close()
            print("Created testdata.txt save file.")
        
async def main():
    print('Connecting to Network...')
    connect_to_network()

    assureSaveFile()

    loadLastState()

    print('Setting up webserver...')
    asyncio.create_task(asyncio.start_server(serve_client, "0.0.0.0", 80))
    asyncio.create_task(everySecondMaintenance())
    while True:
        if button.value():
            hardware_button_pressed()
            await asyncio.sleep(.5)
        elif button_left.value():
            button_left_pressed()
            await asyncio.sleep(.5)
        elif button_right.value():
            button_right_pressed()
            await asyncio.sleep(.5)
        else:
            await asyncio.sleep(.1)
  
try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()
    

    
        
        
    
    
    