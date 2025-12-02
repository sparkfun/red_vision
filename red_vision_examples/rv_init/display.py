# Initializes a display object. Multiple options are provided below, so you can
# choose one that best fits your needs. You may need to adjust the arguments
# based on your specific display and board configuration

# Import the OpenCV display drivers
from red_vision.displays import *

# Import the SPI bus
from .bus_spi import spi

################################################################################
# ST7789
################################################################################

# SPI interface. This should work on any platform, but it's not always the
# fastest option (24Mbps on RP2350)
display = st7789_spi.ST7789_SPI(
    width = 240,
    height = 320,
    spi = spi,
    pin_dc = 16,
    pin_cs = 17,
    rotation = 1
)

# PIO interface. This is only available on Raspberry Pi RP2 processors,
# but is much faster than the SPI interface (75Mbps on RP2350)
# display = st7789_pio.ST7789_PIO(
#     width = 240,
#     height = 320,
#     sm_id = 4,
#     pin_clk = 18,
#     pin_tx = 19,
#     pin_dc = 16,
#     pin_cs = 17,
#     rotation = 1
# )

################################################################################
# DVI
################################################################################

# HSTX interface. This is only available on Raspberry Pi RP2350 processors.
# Create the singleston DVI_HSTX display instance.
# display = dvi_rp2_hstx.DVI_HSTX(
#     width = 320,
#     height = 240,

#     # 4 different color modes are supported, though not all color modes can be
#     # used with all resolutions due to memory constraints.
#     # color_mode = dvi_rp2_hstx.DVI_HSTX.COLOR_BGR233,
#     # color_mode = dvi_rp2_hstx.DVI_HSTX.COLOR_GRAY8,
#     color_mode = dvi_rp2_hstx.DVI_HSTX.COLOR_BGR565,
#     # color_mode = dvi_rp2_hstx.DVI_HSTX.COLOR_BGRA8888,

#     # Pins default to the SparkFun HSTX to DVI Breakout:
#     # https://www.sparkfun.com/sparkfun-hstx-to-dvi-breakout.html
#     # pin_clk_p = 14,
#     # pin_clk_n = 15,
#     # pin_d0_p  = 18,
#     # pin_d0_n  = 19,
#     # pin_d1_p  = 16,
#     # pin_d1_n  = 17,
#     # pin_d2_p  = 12,
#     # pin_d2_n  = 13
# )
