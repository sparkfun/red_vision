#-------------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# 
# Copyright (c) 2025 SparkFun Electronics
#-------------------------------------------------------------------------------
# red_vision_examples/rv_init/touch_screen.py
# 
# This example module initializes a Red Vision touch screen object.
#-------------------------------------------------------------------------------

# Import the Red Vision package.
import red_vision as rv

################################################################################
# CST816
################################################################################

# Import the I2C bus
from .bus_i2c import i2c

# I2C interface
touch_screen = rv.touch_screens.CST816(i2c)
