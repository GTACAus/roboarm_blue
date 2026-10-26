# Robot arm over Bluetooth: the LMS-ESP32 firmware

Firmware for the GTAC robotic arm's LMS-ESP32 board with **Bluetooth instead
of Wi-Fi**. The iPad stays on the school's Wi-Fi, opens the robot controller
from the website (`remote/` at the top of this repo) in the **Bluefy** app, taps
**Connect your robot** and picks the robot (e.g. **ROBOT 7**). The board's
Wi-Fi is never turned on.

It is the robot arm's firmware (legodisco) with its Wi-Fi hotspot, internet
sharing and web server swapped for the Bluetooth link the robot pollinator
proved out (legopollinator, branch `bluetooth`). Everything else is the same:

- **Same hub program.** `SPIKE code/arm-spike-app3.py` is unchanged from
  legodisco: the board still pretends to be a distance sensor on port A, and
  the codes it sends are the same.
- **Same muscle sensor** on IO32 (`app/emg.py`), the same Muscle sensor and
  Remote tabs, the same Blockly code canvas.
- Runs on the LMS-ESP32 v2 (ESP32-PICO-V3-02) and v1 (ESP32-WROVER).

| Part | Where | Runs on |
|---|---|---|
| Firmware: Bluetooth link, muscle sensor, the "distance sensor" | `app/`, `firmware/` | the LMS-ESP32 board |
| Robot controller page | `../remote/` | the website, opened in Bluefy |
| Hub program | `SPIKE code/arm-spike-app3.py` | the SPIKE Prime hub, program slot 0 |
| Provisioning | `tools/provision.py` | the computer that flashes the boards |

## Why Bluetooth

Most of the Wi-Fi build's trouble came from the board doing two networks at
once (a hotspot for the iPad and a link to the school's Wi-Fi for internet):
scans paused the hotspot, the uplink dropped, memory ran short, and IT had to
allow each board. With Bluetooth:

- the iPad never changes network, so the website and the controller work
  together, and the board needs nothing from IT;
- the board runs one radio job, with no web server or NAT, so it has far more
  free memory and nothing that can stall the arm's loop;
- the page lives on the website, so changing it needs no firmware rebuild.

The cost: iPad Safari has no Web Bluetooth, so the controller is opened in
**Bluefy** (free on the App Store). Only one iPad can connect to a robot at a
time.

## How it behaves

- At power-up the board reports the muscle sensor to the hub and advertises
  over Bluetooth under its name.
- The page writes its usual messages (`x=1&m=02200&g=10&p=B&o=0`, plus
  `c=…` commands) one per line; the board replies with the same lines as the
  Wi-Fi version (`m 42`, `h 1 B 11`, `p C 95`, `b C 0`) as notifications.
- **Remote mode** needs the page connected and on the Remote tab, and talking
  within the last 3 s (it sends a heartbeat every 0.5 s). Otherwise the board
  goes back to the muscle sensor, stopping every motor first. A disconnect
  (out of range, iPad asleep) stops the motors at once.
- The muscle reading goes to the page 10 times a second (the Wi-Fi version
  sent 50; Bluetooth has less room).
- The arm's Bluetooth service has its own UUID (`8f3b0001-…`), so the arm's
  controller lists only arms, not pollinators.
- Fixed on the way: a code block's `turn` used to set the muscle amplifier to
  its degrees ÷ 10 (both are `g` in the message) until the next heartbeat.

## How the board and the hub talk

Unchanged from legodisco. The board pretends to be a LEGO Distance Sensor on
hub **port A**.

- **Board → hub**: the distance reading. 50–1000 mm is the muscle signal;
  1100 + 5 × *code* is a command. Codes: 0–34 a motor's run state (motor × 7 +
  state: 0 stop, 1–3 forward slow / medium / fast, 4–6 back), 35 stop all,
  36 home, 37 re-read homes, 38–42 the muscle motor (B–F), 43–87 go-to header,
  88–159 an angle in 5° steps, 160–174 turn header, 175–178 muscle options
  (+1 reverse, +2 no auto return). A command is held for two of the hub's
  reads; the same code twice in a row needs a different reading between.
- **Hub → board**: the sensor's four lights. `1, on` Wi-Fi (ignored: there is
  no Wi-Fi); `2, motor, angle÷100, angle%100` a position; `3, …` a home
  position; `4, mode, muscle motor, fitted-motors mask` status;
  `5, percent, mV÷100, mV%100` battery.

## Flashing a classroom set

One-time setup on the computer:

```bash
pip install esptool mpremote
```

Then, with Thonny closed, from this folder (`lms_esp32`):

```bash
python tools/provision.py
```

The first time it asks for the name before the number (e.g. `ROBOT`). For
each board it reads its MAC, picks its number, wipes it, flashes
`firmware/dist/roboarm-blue.bin`, writes `config.py` (its name) and `main.py`,
and checks that Bluetooth comes on under that name. Numbers are kept in
`tools/boards.csv` (copy legodisco's to keep the same numbers).

A board already set up with the Wi-Fi firmware can be switched without
re-provisioning: its `config.py` has `WIFI_NAME`, which is used as its
Bluetooth name.

```bash
python -m esptool --port COM8 write-flash -z 0x1000 firmware/dist/roboarm-blue.bin
```

## Building the firmware

```bash
firmware/build.sh              # -> firmware/dist/roboarm-blue.bin
firmware/build.sh xiao-test    # -> firmware/dist/roboarm-blue-xiao-test.bin (hub and muscle sensor simulated)
```

It shares MicroPython v1.29 and ESP-IDF v5.5.2 with legodisco
(`~/esp/legodisco-deps`). On Windows, run it in WSL:

```bash
wsl -e bash -lc "cd /mnt/c/Users/<you>/Documents/GitHub/roboarm_blue/lms_esp32 && bash firmware/build.sh"
```

## Trying the controller on a computer

```bash
python tools/mock_board.py      # then open http://localhost:8767
```

serves `../remote/` with a pretend board behind it (motors B, C, E fitted, a
muscle signal that rises and falls). On localhost the page uses HTTP instead
of Bluetooth; `/log` shows what it sent.
