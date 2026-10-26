# Test board: the arm firmware on a XIAO ESP32S3 (e.g. a spare one), with
# the hub and muscle sensor simulated (config.py sets SIMULATE = True) so the Bluetooth remote can
# be tried with no arm attached. Only the chip target and this note differ.
set(IDF_TARGET esp32s3)

set(SDKCONFIG_DEFAULTS
    boards/sdkconfig.base
    boards/sdkconfig.240mhz
    boards/sdkconfig.flash_qio_80m
    boards/sdkconfig.ble
    ${MICROPY_BOARD_DIR}/sdkconfig.board
)

set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest.py)
