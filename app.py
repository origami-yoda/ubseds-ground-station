from flask import Flask, render_template
from flask_socketio import SocketIO

import json
import time
from threading import Thread

app = Flask(__name__)
socketio = SocketIO(app)

def replay_log():
    # Time to wait for replay
    time.sleep(0.5)
    with open("replay.log", "r", encoding="utf-8") as file:
        content = file.readlines()
        line_num = len(content)
        i = 0
        while True:
            # sleep to mimic 10 hz that the fc will send packets
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
    Thread(target=replay_log).start()

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('testingPacket')
def testingPacket(packet):
    print("Received packet: " + packet)

if __name__ == '__main__':
    socketio.run(app, debug=True)