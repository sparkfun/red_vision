#-------------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# 
# Copyright (c) 2025 SparkFun Electronics
#-------------------------------------------------------------------------------
# red_vision_examples/rv_init/bus_spi.py
# 
# This example module initializes an SPI bus for use with other devices.
#-------------------------------------------------------------------------------

# Import the machine.SPI class
from machine import SPI

# Initialize default SPI bus. You may need to adjust the arguments based on your
# specific board and configuration
spi = SPI(
    # id = 0,
    baudrate = 24_000_000, # Use the fastest baudrate you can for best performance!
    # sck = 2,
    # mosi = 3,
    # miso = 4,
)
