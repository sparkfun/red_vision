#-------------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# 
# Copyright (c) 2025 SparkFun Electronics
#-------------------------------------------------------------------------------
# red_vision_examples/rv_init/display.py
# 
# This example module initializes a Red Vision display object. Multiple drivers
# and interfaces are provided for various devices, so you can uncomment whatever
# best fits your needs. You may need to adjust the arguments based on your
# specific display and board configuration. The actual display object is created
# at the end of the file.
#-------------------------------------------------------------------------------

# Import the Red Vision package.
import red_vision as rv

################################################################################
# SPI Display
################################################################################

#############
# Interface #
#############

# Import the SPI bus
from .bus_spi import spi

# Generic SPI interface. This should work on any platform, but it's not always
# the fastest option (24Mbps on RP2350).
interface = rv.displays.SPI_Generic(
    spi = spi,
    pin_dc = 20,
    pin_cs = 21,
)

# PIO interface. This is only available on Raspberry Pi RP2 processors,
# but is much faster than the SPI interface (75Mbps on RP2350).
# interface = rv.displays.SPI_RP2_PIO(
#     sm_id = 4,
#     pin_clk = 22,
#     pin_tx = 23,
#     pin_dc = 20,
#     pin_cs = 21,
# )

##########
# Driver #
##########

# ST7789 display.
driver = rv.displays.ST7789(
    interface = interface,

    # Optionally specify the rotation of the display.
    # rotation = 1,

    # Optionally specify the image resolution.
    # height = 240,
    # width = 320,

    # Optionally specify the image color mode.
    # color_mode = rv.colors.COLOR_MODE_BGR565,

    # Optionally specify the image buffer to use.
    # buffer = None,
)

################################################################################
# DVI/HDMI Display
################################################################################

#############
# Interface #
#############

# HSTX interface. This is only available on Raspberry Pi RP2350 processors.
# interface = rv.displays.DVI_RP2_HSTX(
#     # Pins default to the SparkFun HSTX to DVI Breakout:
#     # https://www.sparkfun.com/sparkfun-hstx-to-dvi-breakout.html
#     # pin_clk_p = 14,
#     # pin_clk_n = 15,
#     # pin_d0_p  = 18,
#     # pin_d0_n  = 19,
#     # pin_d1_p  = 16,
#     # pin_d1_n  = 17,
#     # pin_d2_p  = 12,
#     # pin_d2_n  = 13,
# )

##########
# Driver #
##########

# DVI/HDMI display.
# driver = rv.displays.DVI(
#     interface = interface,

#     # Optionally specify the image resolution.
#     # height = 240,
#     # width = 320,

#     # Optionally specify the image color mode.
#     # color_mode = rv.colors.COLOR_MODE_BGR233,
#     # color_mode = rv.colors.COLOR_MODE_GRAY8,
#     # color_mode = rv.colors.COLOR_MODE_BGR565,
#     # color_mode = rv.colors.COLOR_MODE_BGRA8888,

#     # Optionally specify the image buffer to use.
#     # buffer = None,
# )

################################################################################
# Display Object
################################################################################

# Here we create the main VideoDisplay object using the selected driver.
display = rv.displays.VideoDisplay(driver)
