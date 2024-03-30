import struct
# import serial
import json
import time
from datetime import datetime
# from serial.tools.list_ports import comports
import socketio

crc_table = [
    0x00, 0x07, 0x0e, 0x09, 0x1c, 0x1b, 0x12, 0x15,
    0x38, 0x3f, 0x36, 0x31, 0x24, 0x23, 0x2a, 0x2d,
    0x70, 0x77, 0x7e, 0x79, 0x6c, 0x6b, 0x62, 0x65,
    0x48, 0x4f, 0x46, 0x41, 0x54, 0x53, 0x5a, 0x5d,
    0xe0, 0xe7, 0xee, 0xe9, 0xfc, 0xfb, 0xf2, 0xf5,
    0xd8, 0xdf, 0xd6, 0xd1, 0xc4, 0xc3, 0xca, 0xcd,
    0x90, 0x97, 0x9e, 0x99, 0x8c, 0x8b, 0x82, 0x85,
    0xa8, 0xaf, 0xa6, 0xa1, 0xb4, 0xb3, 0xba, 0xbd,
    0xc7, 0xc0, 0xc9, 0xce, 0xdb, 0xdc, 0xd5, 0xd2,
    0xff, 0xf8, 0xf1, 0xf6, 0xe3, 0xe4, 0xed, 0xea,
    0xb7, 0xb0, 0xb9, 0xbe, 0xab, 0xac, 0xa5, 0xa2,
    0x8f, 0x88, 0x81, 0x86, 0x93, 0x94, 0x9d, 0x9a,
    0x27, 0x20, 0x29, 0x2e, 0x3b, 0x3c, 0x35, 0x32,
    0x1f, 0x18, 0x11, 0x16, 0x03, 0x04, 0x0d, 0x0a,
    0x57, 0x50, 0x59, 0x5e, 0x4b, 0x4c, 0x45, 0x42,
    0x6f, 0x68, 0x61, 0x66, 0x73, 0x74, 0x7d, 0x7a,
    0x89, 0x8e, 0x87, 0x80, 0x95, 0x92, 0x9b, 0x9c,
    0xb1, 0xb6, 0xbf, 0xb8, 0xad, 0xaa, 0xa3, 0xa4,
    0xf9, 0xfe, 0xf7, 0xf0, 0xe5, 0xe2, 0xeb, 0xec,
    0xc1, 0xc6, 0xcf, 0xc8, 0xdd, 0xda, 0xd3, 0xd4,
    0x69, 0x6e, 0x67, 0x60, 0x75, 0x72, 0x7b, 0x7c,
    0x51, 0x56, 0x5f, 0x58, 0x4d, 0x4a, 0x43, 0x44,
    0x19, 0x1e, 0x17, 0x10, 0x05, 0x02, 0x0b, 0x0c,
    0x21, 0x26, 0x2f, 0x28, 0x3d, 0x3a, 0x33, 0x34,
    0x4e, 0x49, 0x40, 0x47, 0x52, 0x55, 0x5c, 0x5b,
    0x76, 0x71, 0x78, 0x7f, 0x6a, 0x6d, 0x64, 0x63,
    0x3e, 0x39, 0x30, 0x37, 0x22, 0x25, 0x2c, 0x2b,
    0x06, 0x01, 0x08, 0x0f, 0x1a, 0x1d, 0x14, 0x13,
    0xae, 0xa9, 0xa0, 0xa7, 0xb2, 0xb5, 0xbc, 0xbb,
    0x96, 0x91, 0x98, 0x9f, 0x8a, 0x8d, 0x84, 0x83,
    0xde, 0xd9, 0xd0, 0xd7, 0xc2, 0xc5, 0xcc, 0xcb,
    0xe6, 0xe1, 0xe8, 0xef, 0xfa, 0xfd, 0xf4, 0xf3
]

class Parser:
    SYNC_WORD = b"\xdb\x69\xc0\x78"
    PKT_LEN = 68
    FLIGHT_PHASES = [
        "Startup",
        "Idle",
        "Launched",
        "DescendingWithDrogue",
        "DescendingWithMain",
        "Landed"
    ]

    def __init__(self):
        self.buf = bytes()
        self.have_sync = False
        self.sync_idx = 0

    def parse(self, data):
        """
        Adds `data` to the parser and returns any new packets that
        it finds in the data that has been added so far.
        """

        # Add the data to the end of the buffer
        self.buf += data

        # Make sure we're synced first
        if not self.have_sync and not self.sync():
            return []

        packets = []

        # Parse packets as long as there is space for another packet in the buffer
        while len(self.buf) >= self.sync_idx + self.PKT_LEN:

            # Ignore additional sync words since we're already synced
            first_word = self.buf[self.sync_idx:self.sync_idx + 4]
            if first_word == self.SYNC_WORD:
                self.sync_idx += 4
                continue

            # Pull the next packet out of the buffer
            pkt_bytes = self.buf[self.sync_idx:self.sync_idx + self.PKT_LEN]
            self.sync_idx += self.PKT_LEN
            raw_acc = [0] * 3
            raw_gyro = [0] * 3
            (millis, apogee, alt, vel, acc, raw_alt, raw_pressure, raw_acc[0], raw_acc[1], raw_acc[2], raw_gyro[0], raw_gyro[1], raw_gyro[2], lat, lon, temp, batt_mv, vref_v, phase, _) = struct.unpack("<IffffffffffffffHHHBB", pkt_bytes)

            # Reset sync if we get an invalid packet
            if phase >= len(self.FLIGHT_PHASES) or \
                    not self.checksum(pkt_bytes):
                self.have_sync = False
                self.sync()
                continue

            packets.append({
                "millis": millis,
                "alt": alt,
                "vel": vel,
                "acc": acc,
                "raw_alt": raw_alt,
                "raw_acc": raw_acc,
                "lat": lat,
                "lon": lon,
                "apogee": apogee,
                "temp": temp / 100,  # Convert to Celsius
                "batt_v": batt_mv / 1000,  # Convert from mV to V
                "phase": self.FLIGHT_PHASES[phase]
            })

        # Now remove all of the data from the buffer that has already been parsed
        self.buf = self.buf[self.sync_idx:]
        self.sync_idx = 0

        return packets

    def checksum(self, pkt_bytes):
        crc = 0
        for b in pkt_bytes:
            crc = crc_table[crc ^ b]
        return crc == 0

    def sync(self):
        idx = self.buf.find(self.SYNC_WORD)
        if idx == -1:
            return False

        # Throw away the sync word and everything before it
        # and set our sync to the start of the buffer.
        self.buf = self.buf[idx + 4:]
        self.sync_idx = 0
        self.have_sync = True
        return True

def read_thread():
    parser = Parser()

    # Replace this with a yaml config thingy
    port = "/dev/ttyUSB0"
    if port is None:
        ports = comports()
        if len(ports) == 1:
            port = ports[0].device
            print("Defaulting to serial port %s", port)
        else:
            print("Unable to determine serial port to use.  Set SERIAL_PORT in config.py")
            return

    print(f"Connecting to {port}")
    try:
        s = serial.Serial(port, baudrate=115200)
    except:
        print("Could not connect to port %s", port)
        print("Using 'replay.log' instead")
        replay_log()

    log_filename = datetime.now().strftime("%Y%m%dT%H%M%S.log")
    with open(log_filename, "a", encoding="utf-8") as log_file:
        while True:
            buf = s.read(parser.PKT_LEN)
            data = parser.parse(buf)
            for msg in data:
                print(msg)
                socketio.emit("data", msg)
                json.dump(msg, log_file)
                log_file.write("\n")

def replay_log():
    # Time to wait for replay
    time.sleep(0.5)
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