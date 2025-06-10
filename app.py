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
RADIO0_PORT    = '/dev/ttyUSB0'   # USB0: send existing commands
RADIO1_PORT    = '/dev/ttyUSB1'   # USB1: recv telemetry + send new commands
BAUDRATE       = 57600
PACKET_SIZE    = 84               # sizeof(aggregatePayload_t)
FMT            = '<I i 11f i 4f 2f I'
LOG_PATH      = 'replay.log'  

# open radio 0 (commands only)
try:
    ser0 = serial.Serial(RADIO0_PORT, BAUDRATE, timeout=1)
    print(f"[+] Opened RADIO0 on {RADIO0_PORT}")
except Exception as e:
    print(f"[!] Could not open RADIO0: {e}")
    ser0 = None

# open radio 1 (telemetry + commands)
try:
    ser1 = serial.Serial(RADIO1_PORT, BAUDRATE, timeout=1)
    print(f"[+] Opened RADIO1 on {RADIO1_PORT}")
except Exception as e:
    print(f"[!] Could not open RADIO1: {e}")
    ser1 = None

#
# ────────────────────────────────────────────────
#   PARSE FUNCTION FOR TELEMETRY (USB1)
# ────────────────────────────────────────────────
#
def parse_packet(data: bytes) -> dict:
    fields = struct.unpack(FMT, data)
    idx = 0

    time_ms = fields[idx]; idx += 1
    phase   = fields[idx]; idx += 1

    kf_pos, kf_vel, kf_accel, altitude = fields[idx:idx+4]; idx += 4
    accel_x, accel_y, accel_z         = fields[idx:idx+3]; idx += 3
    gyro_x, gyro_y, gyro_z            = fields[idx:idx+3]; idx += 3

    pressure_fc = fields[idx]; idx += 1
    temp        = fields[idx]; idx += 1

    voltages        = list(fields[idx:idx+4]); idx += 4
    v_voltages      = list(fields[idx:idx+2]); idx += 2
    pressure_trans  = fields[idx]; idx += 1

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

def read_telemetry_loop():
    """ Continuously read from USB1, emit telemetry """
    if not ser1:
        try:
            print(f"[+] RADIO1 unavailable, replaying JSON from {LOG_PATH}")
            with open(LOG_PATH, 'r') as log_file:
                lines = log_file.readlines()
            if not lines:
                print(f"[!] {LOG_PATH} is empty")
                return

            idx = 0
            while True:
                raw = lines[idx].strip()
                idx = (idx + 1) % len(lines)
                if not raw:
                    continue
                try:
                    payload = json.loads(raw)
                    socketio.emit('telemetry', payload)
                except json.JSONDecodeError as e:
                    print(f"[!] JSON parse error on line {idx}: {e}")

                time.sleep(0.2)

        except Exception as e:
            print(f"[!] Could not open replay log {LOG_PATH}: {e}")
        return
    while True:
        data = ser1.read(PACKET_SIZE)
        if len(data) == PACKET_SIZE:
            try:
                payload = parse_packet(data)
                socketio.emit('telemetry', payload)
                print(f"Telemetry: {json.dumps(payload, indent=2)}")
            except struct.error as e:
                print(f"[!] Parsing error: {e}")
        time.sleep(0.05)

#
# ────────────────────────────────────────────────
#   COMMAND MAPPINGS & ROUTING
# ────────────────────────────────────────────────
#
# USB0 commands (existing set)
radio0_cmds = {
    'q': 'N2 valve ON',
    'w': 'N2 valve OFF',
    'e': 'N2O valve ON',
    'r': 'N2O valve OFF',
    't': 'Tri-state UP',
    'y': 'Tri-state DOWN',
    'u': 'Tri-state STOP',
    'i': 'Igniter ON',
    'o': 'Igniter OFF'
}

# USB1 commands (new set)
radio1_cmds = {
    'a': 'Normally Open ',
    's': 'Cmd S',
    'd': 'Cmd D',
    'f': 'Cmd F'
}

@socketio.on('command')
def handle_command(command):
    desc = radio0_cmds.get(command) or radio1_cmds.get(command) or 'Unknown'
    print(f"COMMAND RECEIVED → '{command}' ({desc})")

    if command in radio0_cmds:
        port, name = ser0, 'RADIO0'
    elif command in radio1_cmds:
        port, name = ser1, 'RADIO1'
    else:
        print("[!] Unknown command; skipping send")
        return {'status': 'error', 'msg': 'unknown command'}

    if port and port.is_open:
        try:
            port.write(command.encode('utf-8'))
            port.flush()
            print(f" → Sent '{command}' on {name}")
            return {'status': 'ok', 'sent_to': name}
        except Exception as e:
            print(f"[!] Error writing to {name}: {e}")
            return {'status': 'error', 'msg': str(e)}
    else:
        print(f"[!] {name} not open; cannot send command")
        return {'status': 'error', 'msg': f'{name} not open'}

#
# ────────────────────────────────────────────────
#   FLASK & SOCKET.IO
# ────────────────────────────────────────────────
#
@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def on_connect():
    print('Client connected')

@socketio.on('disconnect')
def on_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    threading.Thread(target=read_telemetry_loop, daemon=True).start()
    socketio.run(app, debug=True)
