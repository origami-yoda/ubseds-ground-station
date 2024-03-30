from flask import Flask, render_template
from flask_socketio import SocketIO

import json
import time
import serial
from threading import Thread
from radio import Parser
from datetime import datetime
from serial.tools.list_ports import comports
import os

app = Flask(__name__)
socketio = SocketIO(app)

port = 'COM3'
serial_port = None

def read_thread():
    parser = Parser()
    global port 
    # Replace this with a yaml config thing
    if port is None:
        ports = comports()
        if len(ports) == 1:
            port = ports[0].device
            print("Defaulting to serial port", port)
        else:
            print("Unable to determine serial port to use.  Set SERIAL_PORT in config.py")
            return

    print(f"Connecting to {port}")
    try:
        global serial_port 
        serial_port = serial.Serial(port, baudrate=115200)
    except:
        print("Could not connect to port", port)
        print("Using 'replay.log' instead")
        replay_log()

    log_filename = os.path.join('logs/' + datetime.now().strftime("%Y%m%dT%H%M%S.log"))
    with open(log_filename, "a", encoding="utf-8") as log_file:
        while True:
            buf = serial_port.read(parser.PKT_LEN)
            data = parser.parse(buf)
            for msg in data:
                print(msg)
                socketio.emit("data", msg)
                json.dump(msg, log_file)
                log_file.write("\n")

def replay_log():
    # Time to wait for replay
    time.sleep(0.5)
    print("Using replay log...")
    with open("replay.log", "r", encoding="utf-8") as file:
        content = file.readlines()
        line_num = len(content)
        i = 0
        while True:
            # sleep to mimic 5 hz that the fc will send packets
            time.sleep(0.2)
            msg = json.loads(content[i])
            # print(msg)
            socketio.emit("data", msg)
            i = (i + 1) % line_num

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    Thread(target=read_thread).start()

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('testingPacket')
def testingPacket(packet):
    data = packet.get("data")
    # 1 is ejection, 2 is reefing
    # another
    if data == 1:
        serial_port.write("d".encode("utf-8"))
    elif data == 2:
        serial_port.write("m".encode("utf-8"))

if __name__ == '__main__':
    socketio.run(app, debug=True)