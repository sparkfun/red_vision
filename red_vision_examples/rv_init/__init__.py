#-------------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# 
# Copyright (c) 2025 SparkFun Electronics
#-------------------------------------------------------------------------------
# red_vision_examples/rv_init/__init__.py
# 
# This example module initializes various Red Vision hardware components. The
# examples import this module, but you could instead create/edit a `boot.py`
# script to automatically initialize the hardware when the board boots up. See:
# https://micropython.org/resources/docs/en/latest/reference/reset_boot.html#id4
#-------------------------------------------------------------------------------

# When the Red Vision Kit for RedBoard is used with the IoT RedBoard RP2350,
# both the display and camera use GPIO 16-47 instead of GPIO 0-31, so we need to
# adjust the base GPIO for PIO drivers
import rp2
rp2.PIO(1).gpio_base(16)

# Import the camera driver
try:
    from .camera import camera
except:
    print("Camera initialization failed, skipping...")

# Import the display driver
try:
    from .display import display

    # Optional - Show a splash screen on the display with an optional filename
    # (if not provided, it defaults to `splash.png` in the root directory of the
    # MicroPython filesystem). If the file is not present, the driver will
    # simply clear the display of any previous content
    display.splash("red_vision_examples/images/splash.png")
except:
    print("Display initialization failed, skipping...")

# Import the touch screen driver
try:
    from .touch_screen import touch_screen
except:
    print("Touch screen initialization failed, skipping...")

# Mount the SD card
try:
    # We don't actually need to import anything here, just want to run the
    # sd_card module so the SD card gets mounted to the filesystem. So just
    # import something then delete it to avoid clutter
    from .sd_card import sdcard
    del sdcard
except:
    print("SD card initialization failed, skipping...")
