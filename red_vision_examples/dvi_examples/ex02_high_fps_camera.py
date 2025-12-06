#-------------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# 
# Copyright (c) 2025 SparkFun Electronics
#-------------------------------------------------------------------------------
# red_vision_examples/dvi_examples/ex02_high_fps_camera.py
# 
# This example demsontrates how to show a high frame rate camera stream on a DVI
# display. This only works with cameras that support the exact same resolutions
# and color formats as the DVI display, such as the OV5640.
# 
# The DVI driver sends a continuous stream of images to the display, as required
# by the DVI standard, using DMA channels. We can make the camera driver write
# each captured image directly into the DVI display's image buffer, so each
# image gets displayed as soon as it's captured. The camera can also be set to
# run in continuous mode, where DMA channels capture images from the camera as
# fast as possible. Because the camera and display are using DMA channels to
# manage all data transfers, the full frame rate of the camera can be achieved
# with zero CPU overhead.
# 
# Note that this technique is not useful for applications that require image
# processing, due to the shared image buffer.
#-------------------------------------------------------------------------------

# This example does not use the `rv_init` module, in order to demonstrate some
# more advanced features. The initialization is done directly in this example.
import red_vision as rv

# Import NumPy.
from ulab import numpy as np

# Import machine and rp2 for I2C and PIO.
import machine
import rp2

# Image size and bytes per pixel (depends on color mode). This example defaults
# to 320x240 with BGR565.
width = 320
height = 240
color_mode = rv.colors.COLOR_MODE_BGR565
bytes_per_pixel = rv.colors.bytes_per_pixel(color_mode)

# Create the image buffer to be shared between the camera and display.
buffer = np.zeros(
    (height, width, bytes_per_pixel),
    dtype = np.uint8
)

# Verify that the buffer is located in SRAM. If it's in external PSRAM, it
# probably won't work due to the QSPI bus becoming bottlenecked by both the
# camera and display trying to access it at the same time.
if rv.utils.memory.is_in_external_ram(buffer):
    raise MemoryError("Buffer must be in internal RAM for this example")

# Create the HSTX interface.
interface = rv.displays.DVI_RP2_HSTX(
    # Pins default to the SparkFun HSTX to DVI Breakout:
    # https://www.sparkfun.com/sparkfun-hstx-to-dvi-breakout.html
    # pin_clk_p = 14,
    # pin_clk_n = 15,
    # pin_d0_p  = 18,
    # pin_d0_n  = 19,
    # pin_d1_p  = 16,
    # pin_d1_n  = 17,
    # pin_d2_p  = 12,
    # pin_d2_n  = 13,
)

# Initialize the DVI driver using the shared buffer.
driver = rv.displays.DVI(
    interface = interface,

    # Optionally specify the image resolution.
    height = height,
    width = width,

    # Optionally specify the image color mode.
    color_mode = color_mode,

    # Optionally specify the image buffer to use.
    buffer = buffer,
)

# Create the VideoDisplay object.
display = rv.displays.VideoDisplay(driver)

# Initialize the OV5640 camera, using the shared buffer.
i2c = machine.I2C()
rp2.PIO(1).gpio_base(16)

# Create the PIO interface.
interface = rv.cameras.DVP_RP2_PIO(
    sm_id = 5,
    pin_d0 = 28,
    pin_vsync = 42,
    pin_hsync = 41,
    pin_pclk = 40,

    # Optionally specify the XCLK pin if needed by your camera.
    pin_xclk = 44,
)

# Initialize the OV5640 driver using the shared buffer.
driver = rv.cameras.OV5640(
    interface,
    i2c,

    # Optionally run in continuous capture mode.
    continuous = True,

    # Optionally specify the image resolution.
    height = height,
    width = width,

    # Optionally specify the image color mode.
    color_mode = color_mode,

    # Optionally specify the image buffer to use.
    buffer = buffer,
)

# Create the VideoCapture object.
camera = rv.cameras.VideoCapture(driver)

# Open the camera to start the continuous capture process.
camera.open()
camera.grab()
