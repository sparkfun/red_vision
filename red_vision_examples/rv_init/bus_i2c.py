#-------------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# 
# Copyright (c) 2025 SparkFun Electronics
#-------------------------------------------------------------------------------
# red_vision_examples/rv_init/bus_i2c.py
# 
# This example module initializes an I2C bus for use with other devices.
#-------------------------------------------------------------------------------

# Import the machine.I2C class
from machine import I2C

# Initialize default I2C bus. You may need to adjust the arguments based on your
# specific board and configuration
i2c = I2C(
    # id = 0,
    # sda = 0,
    # scl = 1,
    # freq = 100_000
)
