# app.py
import os
import serial
from flask import Flask, render_template
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)

#
# ────────────────────────────────────────────────
#   SERIAL SETUP
# ────────────────────────────────────────────────
#
# Change this to whatever your FTDI shows up as:
SERIAL_PORT_NAME = '/dev/ttyUSB0'
BAUDRATE = 57600

try:
    serial_port = serial.Serial(SERIAL_PORT_NAME,
                                baudrate=BAUDRATE,
                                timeout=1)
    print(f"[+] Opened serial port {SERIAL_PORT_NAME} @ {BAUDRATE} baud")
except Exception as e:
    print(f"[!] Failed to open serial port {SERIAL_PORT_NAME}: {e}")
    serial_port = None


#
# ────────────────────────────────────────────────
#   FLASK ROUTES & SOCKET HANDLERS
# ────────────────────────────────────────────────
#
@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('connect')
def handle_connect():
    print('Client connected')


@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')


@socketio.on('command')
def handle_command(command):
    """
    Receives a single‐char command from the browser and
    forwards it to the serial port.
    """
    # 1) Echo to terminal:
    desc = {
        'q': 'N2 valve ON',
        'w': 'N2 valve OFF',
        'e': 'N2O valve ON',
        'r': 'N2O valve OFF',
        't': 'Tri‐state UP',
        'y': 'Tri‐state DOWN',
        'u': 'Tri‐state STOP',
        'i': 'Igniter ON',
        'o': 'Igniter OFF'
    }.get(command, 'Unknown')

    print(f"COMMAND RECEIVED → '{command}' ({desc})")

    # 2) Send out over serial if available
    if serial_port and serial_port.is_open:
        try:
            # write expects bytes
            serial_port.write(command.encode('utf-8'))
            serial_port.flush()
            print(f" → Sent '{command}' over serial")
        except Exception as e:
            print(f"[!] Error writing to serial: {e}")
    else:
        print("[!] Serial port not open, skipping write")

    # 3) Optionally ack back to client
    return {'status': 'ok'}


if __name__ == '__main__':
    # If you run under eventlet/gevent, Flask‐SocketIO will auto‐serve.
    socketio.run(app, debug=True)
