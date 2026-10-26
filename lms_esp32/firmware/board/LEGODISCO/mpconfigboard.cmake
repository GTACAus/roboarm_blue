# LMS-ESP32 (v2: ESP32-PICO-V3-02; v1: ESP32-WROVER) running the GTAC robot arm: the iPad page
# connects over Bluetooth (app/ble.py) and the board passes its commands to the SPIKE hub on port A, with the muscle sensor on IO32.
# The board's Wi-Fi is never turned on. PSRAM is not used (not needed, and on the original ESP32 it
# would slow every program down with a compiler workaround).
set(IDF_TARGET esp32)

set(SDKCONFIG_DEFAULTS
    boards/sdkconfig.base
    boards/sdkconfig.ble
    ${MICROPY_BOARD_DIR}/sdkconfig.board
)

set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest.py)
