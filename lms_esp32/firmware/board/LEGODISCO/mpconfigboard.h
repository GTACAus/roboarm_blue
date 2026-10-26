#ifndef MICROPY_HW_BOARD_NAME
#define MICROPY_HW_BOARD_NAME "LMS-ESP32 GTAC robot arm (Bluetooth)"
#endif
#define MICROPY_HW_MCU_NAME "ESP32"

// No mDNS: the board has no network (the remote connects over Bluetooth)
#define MICROPY_HW_ENABLE_MDNS_QUERIES (0)
#define MICROPY_HW_ENABLE_MDNS_RESPONDER (0)
