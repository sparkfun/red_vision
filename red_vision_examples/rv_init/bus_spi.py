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

# Some boards use the same SPI bus for both the display and the SD card, others
# have separate buses. We'll create a separate `spi_sd` object for the SD card.
import sys
if "IoT RedBoard RP2350" in sys.implementation._machine:
    spi_sd = SPI(
        1,
        baudrate = 24_000_000,
    )
else:
    spi_sd = spi
