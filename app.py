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

port = '/dev/tty.usbserial-FT7212XY'
serial_port = None

# Connecting to serial port
def read_thread():
    # parser class to go frmo bytes to JSON
    parser = Parser()
    global port 
    # Replace this with a yaml config thing (this is a Mistah Nate thing)
    if port is None:
        ports = comports()
        if len(ports) == 1:
            port = ports[0].device
            print("Defaulting to serial port", port)
        else:
            print("Unable to determine serial port to use. Set port variable")
            return

    print(f"Connecting to {port}")
    try:
        global serial_port 
        serial_port = serial.Serial(port, baudrate=115200)
    except Exception as e:
        print("Could not connect to port", port)
        print("Using 'replay.log' instead")
        print(e)
        # If we arent connected to a serial port, we use the replay file to test
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
    time.sleep(0.2)
    print("Using replay log...")
    with open("logs/replay.log", "r", encoding="utf-8") as file:
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

# sending infomation back through the serial port
@socketio.on('testingPacket')
def testingPacket(packet):
    print(str(packet))
    serial_port.write(packet.encode("utf-8"))
    

if __name__ == '__main__':
    socketio.run(app, debug=True)