"""Flash LMS-ESP32 boards one after another and name them ROBOT 1, ROBOT 2, ...

    python tools/provision.py                  number new boards from 1 (or the next free number)
    python tools/provision.py --start 12       number new boards from 12
    python tools/provision.py --number 7       flash one board as ROBOT 7 (e.g. a replacement)
    python tools/provision.py --port COM5      use this port instead of waiting for a new one
    python tools/provision.py --ask            ask for the name prefix again

The name before the number (e.g. ROBOT) is asked the first time and kept in
tools/site.json (ignored by git). Each board gets its name in its own
config.py: the name the iPad shows when it connects over Bluetooth.

Plug in a board when asked; it is wiped, flashed, named and checked, then you
are asked for the next one. Each board's number is remembered by its MAC
address in tools/boards.csv, so re-flashing a board keeps its name.

Needs: pip install esptool mpremote    (close Thonny first: it holds the port)
"""
import argparse
import csv
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    sys.exit("Needs esptool and mpremote: pip install esptool mpremote")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIRMWARE = os.path.join(ROOT, "firmware", "dist", "roboarm-blue.bin")
MAIN_PY = os.path.join(ROOT, "app", "main.py")
LOG = os.path.join(ROOT, "tools", "boards.csv")
SITE = os.path.join(ROOT, "tools", "site.json")
BOOT_CHECK_S = 25        # time allowed for the board to boot and turn Bluetooth on


def run(*cmd, quiet=True):
    r = subprocess.run([sys.executable, "-m"] + list(cmd), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("%s failed:\n%s" % (" ".join(cmd[:3]), (r.stdout + r.stderr)[-1500:]))
    if not quiet:
        print(r.stdout)
    return r.stdout + r.stderr


CHIP = "esp32"               # set from --chip in main()
FLASH_OFFSET = "0x1000"      # where the firmware image starts: esp32 0x1000, esp32s3/c3 0x0


def esptool(port, command, *args):
    baud = "460800" if CHIP == "esp32s3" else "921600"
    base = ["esptool", "--chip", CHIP, "--port", port, "--baud", baud]
    if CHIP == "esp32s3":
        base.extend(["--before", "usb-reset", "--after", "no-reset"])
    try:
        return run(*(base + [command] + list(args)))
    except RuntimeError as e:
        if "invalid choice" not in str(e):
            raise
        return run(*(base + [command.replace("-", "_")] + list(args)))


def usb_ports():
    return {p.device for p in list_ports.comports() if p.vid is not None}


def wait_for_board(known):
    """Wait until a USB serial port appears that wasn't there before."""
    print("\nPlug in the next board (Ctrl+C to finish)...", flush=True)
    while True:
        now = usb_ports()
        new = now - known
        if new:
            time.sleep(1.0)      # let the port settle
            return sorted(new)[0]
        known &= now             # a board unplugged: its port may come back as "new"
        time.sleep(0.3)


def load_log():
    boards = {}
    if os.path.exists(LOG):
        with open(LOG, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                boards[row["mac"]] = int(row["number"])
    return boards


def save_log(number, mac, sta_mac):
    """Append a row. `mac` is the board's base MAC (its identity, read before
    flashing); `sta_mac` is the MAC its firmware reports (the same chip's)."""
    new = not os.path.exists(LOG)
    with open(LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["number", "mac", "sta_mac", "flashed"])
        w.writerow([number, mac, sta_mac or "", datetime.datetime.now().isoformat(timespec="seconds")])


def ask(prompt, default="", check=None):
    while True:
        value = input("%s%s: " % (prompt, " [%s]" % default if default else "")).strip() or default
        problem = check(value) if check else None
        if not problem:
            return value
        print("   " + problem)


def site_settings(args):
    """The name before each board's number: from the command line, tools/site.json, or asked."""
    saved = {}
    if os.path.exists(SITE) and not args.ask:
        with open(SITE, encoding="utf-8") as f:
            saved = json.load(f)
    prefix = args.prefix or saved.get("prefix")
    if prefix:
        print('Boards are named "%s n"' % prefix)
        return {"prefix": prefix}
    prefix = ask("Robot name, before the number", "ROBOT",
                 check=lambda v: None if 1 <= len(v) <= 24 else "1 to 24 characters")
    with open(SITE, "w", encoding="utf-8") as f:
        json.dump({"prefix": prefix}, f, indent=2)
    return {"prefix": prefix}


def write_board_files(port, name, site, simulate=False):
    lines = ["# This board's name: what the iPad shows over Bluetooth (written by tools/provision.py).",
             "ROBOT_NAME = %r" % name]
    if simulate:
        lines.append("SIMULATE = True   # fake the hub and muscle sensor (test board)")
    # UTF-8 whatever the computer's default (MicroPython reads UTF-8)
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
        config = f.name
    try:
        print("   waiting for board to boot...", flush=True)
        time.sleep(3)
        for attempt in range(5):     # the first boot formats the filesystem; give it time
            try:
                run("mpremote", "connect", port, "fs", "cp", config, ":config.py", "+",
                    "fs", "cp", MAIN_PY, ":main.py", "+", "reset")
                return
            except RuntimeError:
                if attempt == 4:
                    raise
                time.sleep(2)
    finally:
        os.unlink(config)


def open_serial(port):
    # Open with DTR and RTS off: they drive the board's reset and boot pins,
    # and some drivers (notably on Windows) pulse them as the port opens.
    s = serial.Serial()
    s.port, s.baudrate, s.timeout = port, 115200, 0.5
    s.dtr = s.rts = False
    s.open()
    return s


def check_boot(port, name):
    """Watch the board start up. Returns (Bluetooth came on with this name, MAC or None).
    Tolerates the port dropping and coming back: a board with native USB (the
    XIAO ESP32S3 test board) re-enumerates when it resets, sometimes under a
    new name."""
    deadline = time.time() + BOOT_CHECK_S
    ok = False
    sta_mac = None
    s = None
    while time.time() < deadline:
        try:
            if s is None:
                p = port if os.path.exists(port) else (sorted(usb_ports()) or [port])[0]
                s = open_serial(p)
            line = s.readline().decode(errors="replace").strip()
        except (OSError, serial.SerialException):
            if s is not None:
                try:
                    s.close()
                except Exception:
                    pass
                s = None
            time.sleep(0.3)
            continue
        if not line:
            continue
        if line.startswith(("Bluetooth on", "Python heap", "Error", "STA-MAC")):
            print("   board: " + line)
        if line.startswith("STA-MAC "):
            sta_mac = line.split(None, 1)[1].strip().lower()
        if line == "Bluetooth on: " + name:
            ok = True
        if ok and line.startswith("Python heap"):
            break
    if s is not None:
        s.close()
    return ok, sta_mac


def provision(port, number, args, site, log):
    names = site["prefix"] + " %d"
    print("\n== %s on %s" % (names % number if number else "board", port))
    out = esptool(port, "read-mac")
    mac = re.search(r"MAC:\s*([0-9a-f:]{17})", out, re.I).group(1).lower()
    if not number:
        number = log.get(mac) or next(n for n in range(args.start, 1000) if n not in log.values())
    name = names % number
    print("   MAC %s -> %s%s" % (mac, name, " (as before)" if log.get(mac) == number else ""))
    print("   erasing and flashing...", flush=True)
    if CHIP == "esp32s3":
        esptool(port, "write-flash", "--erase-all", "-z", FLASH_OFFSET, args.firmware)
    else:
        esptool(port, "erase-flash")
        esptool(port, "write-flash", "-z", FLASH_OFFSET, args.firmware)
    print("   writing config...", flush=True)
    time.sleep(3)                    # first boot
    write_board_files(port, name, site, args.simulate)
    ok, sta_mac = check_boot(port, name)
    if ok:
        print("\a   OK. Label this board: %s" % name)
    else:
        print("\a   !! %s did not report Bluetooth coming on; check it in Thonny." % name)
    log[mac] = number
    save_log(number, mac, sta_mac)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--start", type=int, default=1, help="first number for new boards")
    p.add_argument("--number", type=int, help="flash a single board with this number")
    p.add_argument("--port", help="serial port (default: wait for a board to be plugged in)")
    p.add_argument("--firmware", default=FIRMWARE)
    p.add_argument("--prefix", help='name before the number (e.g. "ROBOT")')
    p.add_argument("--ask", action="store_true", help="ask for the name prefix again")
    p.add_argument("--chip", default="esp32", help="esp32 (default) or esp32s3 for the XIAO test board")
    p.add_argument("--simulate", action="store_true",
                   help="write SIMULATE=True (fake hub, for a test board)")
    args = p.parse_args()

    global CHIP, FLASH_OFFSET
    CHIP = args.chip
    FLASH_OFFSET = "0x0" if args.chip != "esp32" else "0x1000"

    if not os.path.exists(args.firmware):
        sys.exit("No firmware at %s: run firmware/build.sh first" % args.firmware)

    site = site_settings(args)
    log = load_log()
    known = usb_ports()
    if args.port or args.number:
        port = args.port or (sorted(known)[0] if len(known) == 1 else wait_for_board(known))
        provision(port, args.number, args, site, log)
        return
    try:
        while True:
            port = wait_for_board(known)
            try:
                provision(port, None, args, site, log)
            except Exception as e:
                print("\a   !! Failed: %s" % e)
            print("   Unplug the board.")
            while port in usb_ports():
                time.sleep(0.3)
            known = usb_ports()
    except KeyboardInterrupt:
        print("\nDone. Boards so far: %s" % ", ".join(
            "%s %d" % (site["prefix"], n) for n in sorted(set(log.values()))))


if __name__ == "__main__":
    main()
