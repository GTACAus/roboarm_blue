# Only what the arm needs: the port's own startup modules (filesystem mount
# etc.) and the app, frozen so it runs from flash and leaves the Python heap for
# live data.
freeze("$(PORT_DIR)/modules")
freeze("$(BOARD_DIR)/../../../app", ("arm.py", "lump.py", "emg.py", "ble.py"))
