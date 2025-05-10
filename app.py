import serial
import struct
import time
import threading
import json
from flask import Flask, render_template
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)

#
# ────────────────────────────────────────────────
#   SERIAL SETUP
# ────────────────────────────────────────────────
#
SERIAL_PORT_NAME = '/dev/ttyUSB0'
BAUDRATE = 57600
PACKET_SIZE = 84  # sizeof(aggregatePayload_t) on the STM32 side

# little-endian struct format (must match your STM32 layout)
FMT = '<I i 11f h 2x 4f 2f I'

try:
    serial_port = serial.Serial(SERIAL_PORT_NAME, baudrate=BAUDRATE, timeout=1)
    print(f"[+] Opened serial port {SERIAL_PORT_NAME} @ {BAUDRATE} baud")
except Exception as e:
    print(f"[!] Failed to open serial port {SERIAL_PORT_NAME}: {e}")
    serial_port = None

def parse_packet(data: bytes) -> dict:
    fields = struct.unpack(FMT, data)
    idx = 0

    # flightComputerPayload_t
    time_ms = fields[idx]; idx += 1
    phase   = fields[idx]; idx += 1

    kf_pos, kf_vel, kf_accel, altitude = fields[idx:idx+4]; idx += 4
    accel_x, accel_y, accel_z         = fields[idx:idx+3]; idx += 3
    gyro_x, gyro_y, gyro_z            = fields[idx:idx+3]; idx += 3

    pressure_fc = fields[idx]; idx += 1
    temp        = fields[idx]; idx += 1

    # powerBoardPayload_t
    voltages = list(fields[idx:idx+4]); idx += 4

    # valveBoardPayload_t
    v_voltages = list(fields[idx:idx+2]); idx += 2
    pressure_trans = fields[idx]; idx += 1

    return {
        "flightComputer": {
            "time_ms": time_ms,
            "phase": phase,
            "kf": {"pos": kf_pos, "vel": kf_vel, "accel": kf_accel},
            "altitude": altitude,
            "accel": {"x": accel_x, "y": accel_y, "z": accel_z},
            "gyro": {"x": gyro_x, "y": gyro_y, "z": gyro_z},
            "pressure": pressure_fc,
            "temp": temp
        },
        "powerBoard": {"voltages": voltages},
        "valveBoard": {
            "voltages": v_voltages,
            "pressureTransducer": pressure_trans
        }
    }

def read_serial_loop():
    if not serial_port:
        return
    while True:
        data = serial_port.read(PACKET_SIZE)
        if len(data) == PACKET_SIZE:
            try:
                payload = parse_packet(data)
                # emit telemetry JSON to all connected web clients
                socketio.emit('telemetry', payload)
                print(f"Telemetry: {json.dumps(payload, indent=2)}")
            except struct.error as e:
                print(f"[!] Parsing error: {e}")
        time.sleep(0.05)

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
    desc = {
        'q': 'N2 valve ON',
        'w': 'N2 valve OFF',
        'e': 'N2O valve ON',
        'r': 'N2O valve OFF',
        't': 'Tri-state UP',
        'y': 'Tri-state DOWN',
        'u': 'Tri-state STOP',
        'i': 'Igniter ON',
        'o': 'Igniter OFF'
    }.get(command, 'Unknown')

    print(f"COMMAND RECEIVED → '{command}' ({desc})")

    if serial_port and serial_port.is_open:
        try:
            serial_port.write(command.encode('utf-8'))
            serial_port.flush()
            print(f" → Sent '{command}' over serial")
        except Exception as e:
            print(f"[!] Error writing to serial: {e}")
    else:
        print("[!] Serial port not open, skipping write")

    return {'status': 'ok'}

if __name__ == '__main__':
    # start background thread to read and emit telemetry
    threading.Thread(target=read_serial_loop, daemon=True).start()
    # start Flask-SocketIO server
    socketio.run(app, debug=True)
