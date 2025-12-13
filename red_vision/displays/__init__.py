#-------------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# 
# Copyright (c) 2025 SparkFun Electronics
#-------------------------------------------------------------------------------
# red_vision/displays/__init__.py
# 
# Imports all available Red Vision display drivers.
#-------------------------------------------------------------------------------

# Import the generic VideoDisplay class.
from .video_display import VideoDisplay

# Import platform agnostic drivers.
from .st7789 import ST7789
from .spi_generic import SPI_Generic
from .dvi import DVI

# Import platform specific drivers.
import sys
if 'rp2' in sys.platform:
    from .spi_rp2_pio import SPI_RP2_PIO
    from .dvi_rp2_hstx import DVI_RP2_HSTX
