#-------------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# 
# Copyright (c) 2025 SparkFun Electronics
#-------------------------------------------------------------------------------
# red_vision_examples/rv_init/camera.py
# 
# This example module initializes a Red Vision camera object. Multiple drivers
# and interfaces are provided for various devices, so you can uncomment whatever
# best fits your needs. You may need to adjust the arguments based on your
# specific camera and board configuration. The actual camera object is created
# at the end of the file.
#-------------------------------------------------------------------------------

# Import the Red Vision package.
import red_vision as rv

################################################################################
# DVP Camera
################################################################################

#############
# Interface #
#############

# Import the I2C bus.
from .bus_i2c import i2c

# PIO interface, only available on Raspberry Pi RP2 processors.
interface = rv.cameras.DVP_RP2_PIO(
    sm_id = 5,
    pin_d0 = 28,
    pin_vsync = 42,
    pin_hsync = 41,
    pin_pclk = 40,

    # Optionally specify the XCLK pin if needed by your camera.
    pin_xclk = 44,
)

##########
# Driver #
##########

# HM01B0 camera.
driver = rv.cameras.HM01B0(
    interface,
    i2c,

    # Optionally specify the number of data pins for the camera to use.
    # num_data_pins = 1, # Number of data pins used by the camera (1, 4, or 8)

    # Optionally run in continuous capture mode.
    # continuous = False,

    # Optionally specify the image resolution.
    # height = 244,
    # width = 324,

    # Optionally specify the image buffer to use.
    # buffer = None,
)

# OV5640 camera.
# driver = rv.cameras.OV5640(
#     interface,
#     i2c,

#     # Optionally run in continuous capture mode.
#     # continuous = False,

#     # Optionally specify the image resolution.
#     # height = 240,
#     # width = 320,

#     # Optionally specify the image color mode.
#     # color_mode = rv.colors.COLOR_MODE_BGR565,

#     # Optionally specify the image buffer to use.
#     # buffer = None,
# )

################################################################################
# Camera Object
################################################################################

# Here we create the main VideoCapture object using the selected driver.
camera = rv.cameras.VideoCapture(driver)
