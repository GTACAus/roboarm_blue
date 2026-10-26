# GTAC robotic arm: the link between the iPad page and the board, over Bluetooth.
# The iPad stays on the school's Wi-Fi, opens the arm page (remote/) from the website in Bluefy (or
# another browser with Web Bluetooth) and connects to the board, which shows up under its name (ROBOT 7).
#
# The page's messages ("x=1&m=02200&g=10&p=B&o=0&c=turn&k=E&g=90&v=1") are written to RX, one per
# line; the board's replies and news ("m 42", "h 1 B 11", "p C 95") are notified on TX, one per line.
# arm.py uses page_open(), poll() and broadcast().
#
# The service UUID differs from the robot pollinator's (8f3a...), so the arm page lists only arms.

import bluetooth
import utime
from micropython import const

SERVICE = bluetooth.UUID("8f3b0001-5e0b-4c8e-9a1d-7c2b3e4f5a60")
RX_UUID = bluetooth.UUID("8f3b0002-5e0b-4c8e-9a1d-7c2b3e4f5a60")   # page -> board (write)
TX_UUID = bluetooth.UUID("8f3b0003-5e0b-4c8e-9a1d-7c2b3e4f5a60")   # board -> page (notify)

PAGE_TIMEOUT_MS = 3000         # the page counts as open while it has spoken within this time
REPLY_MS = 1000                # the status reply to the page's messages goes out at most this often
ADVERTISE_US = 100000          # advertising interval while waiting for an iPad

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_MTU_EXCHANGED = const(21)


def parse(text):
    """'m=00300&x=1' -> {'m': '00300', 'x': '1'}"""
    d = {}
    for part in text.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            d[k] = v
    return d


def _adv(field, value):
    return bytes((len(value) + 1, field)) + value


class Ble:
    def __init__(self, on_message, name):
        """on_message(dict) -> reply text. Called for every message from the page."""
        self.on_message = on_message
        self.name = name
        self.conn = None
        self.mtu = 23
        self.written = False                 # set by the interrupt handler: RX has data
        self.lost = False                    # set by the interrupt handler: the iPad left
        self.partial = b""
        self.last_message = utime.ticks_add(utime.ticks_ms(), -PAGE_TIMEOUT_MS - 1)
        self.last_reply = self.last_message
        self.ble = bluetooth.BLE()
        self.ble.active(True)
        self.ble.config(gap_name=name, mtu=247)
        self.ble.irq(self._irq)
        ((self.tx, self.rx),) = self.ble.gatts_register_services((
            (SERVICE, ((TX_UUID, bluetooth.FLAG_NOTIFY | bluetooth.FLAG_READ),
                       (RX_UUID, bluetooth.FLAG_WRITE | bluetooth.FLAG_WRITE_NO_RESPONSE))),))
        self.ble.gatts_set_buffer(self.rx, 512, True)   # writes add up until read, so long lines survive
        # Advertising: the service (so the page can find it) and, in the scan response, the name
        uuid = bytes(SERVICE)
        self.adv = _adv(0x01, b"\x06") + _adv(0x07, uuid)
        self.resp = _adv(0x09, name.encode())
        self._advertise()
        print("Bluetooth on:", name)

    def _advertise(self):
        try:
            self.ble.gap_advertise(ADVERTISE_US, adv_data=self.adv, resp_data=self.resp)
        except Exception as e:
            print("Bluetooth advertising failed:", e)

    def _irq(self, event, data):
        # Runs in interrupt context: only note what happened; poll() does the work
        if event == _IRQ_CENTRAL_CONNECT:
            self.conn = data[0]
            self.mtu = 23
        elif event == _IRQ_CENTRAL_DISCONNECT:
            self.conn = None
            self.lost = True
        elif event == _IRQ_GATTS_WRITE and data[1] == self.rx:
            self.written = True
        elif event == _IRQ_MTU_EXCHANGED:
            self.mtu = data[1]

    def page_open(self):
        return self.conn is not None and utime.ticks_diff(utime.ticks_ms(), self.last_message) < PAGE_TIMEOUT_MS

    def poll(self):
        if self.lost:
            self.lost = False
            self.partial = b""
            self.last_message = utime.ticks_add(utime.ticks_ms(), -PAGE_TIMEOUT_MS - 1)   # stop the motors now
            print("Bluetooth: the iPad disconnected")
            self._advertise()
        if not self.written:
            return
        self.written = False
        data = self.partial + self.ble.gatts_read(self.rx)
        lines = data.split(b"\n")
        self.partial = lines.pop()[-512:]
        reply = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            self.last_message = utime.ticks_ms()
            try:
                reply = self.on_message(parse(line.decode()))
            except Exception as e:
                print("Bad message:", e)
        now = utime.ticks_ms()
        if reply and utime.ticks_diff(now, self.last_reply) >= REPLY_MS:
            self.last_reply = now
            self.broadcast(reply)

    def broadcast(self, text):
        """Send lines to the page, in pieces that fit the link."""
        conn = self.conn
        if conn is None:
            return
        data = text.encode() + b"\n"
        size = max(20, self.mtu - 3)
        for i in range(0, len(data), size):
            try:
                self.ble.gatts_notify(conn, self.tx, data[i:i + size])
            except Exception:
                return              # the link is busy or gone: the next reply brings the page up to date
