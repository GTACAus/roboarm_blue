# Same frozen app as the real board, plus simhub.py (the fake hub and muscle sensor).
freeze("$(PORT_DIR)/modules")
freeze("$(BOARD_DIR)/../../../app", ("arm.py", "lump.py", "emg.py", "ble.py", "simhub.py"))
