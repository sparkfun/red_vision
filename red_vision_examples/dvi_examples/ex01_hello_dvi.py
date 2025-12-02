#-------------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# 
# Copyright (c) 2025 SparkFun Electronics
#-------------------------------------------------------------------------------
# ex01_hello_dvi.py
# 
# This example can be used to verify that DVI output is functioning correctly
# on your board. It creates a simple test image with various colors and shapes,
# and shows it on the display. Only boards with the RP2350 are supported.
#-------------------------------------------------------------------------------

# This example does not use the `rv_init` module, in order to demonstrate some
# more advanced features of the DVI display driver. So we instead import the
# display driver here.
from red_vision.displays import dvi_rp2_hstx

# Import OpenCV and NumPy.
import cv2 as cv
from ulab import numpy as np

# Image size. The DVI driver currently only supports fractions of 640x480 (eg.
# 320x240), optionally with different fractions for width and height (eg.
# 320x480), and repeats pixels and rows to upscale to 640x480 for output.
width = 320
height = 240

# Create the singleston DVI_HSTX display instance.
display = dvi_rp2_hstx.DVI_HSTX(
    width = width,
    height = height,

    # 4 different color modes are supported, though not all color modes can be
    # used with all resolutions due to memory constraints.
    # color_mode = dvi_rp2_hstx.DVI_HSTX.COLOR_BGR233,
    # color_mode = dvi_rp2_hstx.DVI_HSTX.COLOR_GRAY8,
    color_mode = dvi_rp2_hstx.DVI_HSTX.COLOR_BGR565,
    # color_mode = dvi_rp2_hstx.DVI_HSTX.COLOR_BGRA8888,

    # Pins default to the SparkFun HSTX to DVI Breakout:
    # https://www.sparkfun.com/sparkfun-hstx-to-dvi-breakout.html
    # pin_clk_p = 14,
    # pin_clk_n = 15,
    # pin_d0_p  = 18,
    # pin_d0_n  = 19,
    # pin_d1_p  = 16,
    # pin_d1_n  = 17,
    # pin_d2_p  = 12,
    # pin_d2_n  = 13
)

# OpenCV doesn't have a BGR233 color conversion, so if we're using that mode,
# we need to create our test image with single channel values.
if display._color_mode == dvi_rp2_hstx.DVI_HSTX.COLOR_BGR233:
    image_channels = 1
    # BGR233 packs each byte as follows: RRRGGGBB
    color_red     = (0xE0)
    color_green   = (0x1C)
    color_blue    = (0x03)
    color_yellow  = (0xFC)
    color_cyan    = (0x1F)
    color_magenta = (0xE3)
    color_white   = (0xFF)
    color_gray    = (0x92)
    color_black   = (0x00)
else:
    image_channels = 3
    color_red     = (0, 0, 255)
    color_green   = (0, 255, 0)
    color_blue    = (255, 0, 0)
    color_yellow  = (0, 255, 255)
    color_cyan    = (255, 255, 0)
    color_magenta = (255, 0, 255)
    color_white   = (255, 255, 255)
    color_gray    = (128, 128, 128)
    color_black   = (0, 0, 0)

# Create a test image with various colors and shapes.
img = np.zeros((height, width, image_channels), dtype=np.uint8)
img[:, :] = color_gray
img[ 0:10, 0:10] = color_red
img[10:20, 0:10] = color_green
img[20:30, 0:10] = color_blue
img[00:10,10:20] = color_yellow
img[10:20,10:20] = color_cyan
img[20:30,10:20] = color_magenta
img[ 0:30,20:30] = color_white
img = cv.ellipse(img, (160, 120), (100, 50), 0, 0, 360, color_black, -1)
img = cv.putText(img, "Hello DVI!", (80, 200), cv.FONT_HERSHEY_SIMPLEX, 1, color_white, 2)
img = cv.putText(img, "Red!", (20, 60), cv.FONT_HERSHEY_SIMPLEX, 1, color_red, 2)
img = cv.putText(img, "Green!", (100, 60), cv.FONT_HERSHEY_SIMPLEX, 1, color_green, 2)
img = cv.putText(img, "Blue!", (220, 60), cv.FONT_HERSHEY_SIMPLEX, 1, color_blue, 2)

# Show the test image.
display.imshow(img)

# Draw a color gradient test pattern directly into the display buffer.
for i in range(256):
    display._buffer[0:10, width - 256 + i] = i

# When writing the display buffer directly, if its buffer is in PSRAM, some
# pixels may not update until a garbage collection cycle occurs. This is because
# the DVI driver uses the XIP streaming interface to read directly from PSRAM,
# which bypasses the XIP cache.
if display._buffer_is_in_psram:
    import gc
    gc.collect()

# If the ST7789 display is also connected, it can be controlled independently
# of the DVI display. For example, we can show a splash screen on it:
from red_vision.displays import st7789_pio
spi = machine.SPI(baudrate=24_000_000)
display2 = st7789_pio.ST7789_PIO(
    width = 240,
    height = 320,
    sm_id = 4,
    pin_clk = 22,
    pin_tx = 23,
    pin_dc = 20,
    pin_cs = 21,
    rotation = 1
)
display2.splash("red_vision_examples/images/splash.png")
