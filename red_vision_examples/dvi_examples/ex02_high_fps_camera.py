#-------------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# 
# Copyright (c) 2025 SparkFun Electronics
#-------------------------------------------------------------------------------
# ex02_high_fps_camera.py
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
# more advanced features of the drivers. So we instead import the drivers here.
from red_vision.displays import dvi_rp2_hstx
from red_vision.cameras import ov5640_pio

# Import NumPy.
from ulab import numpy as np

# Import addressof from uctypes.
from uctypes import addressof

# Import machine and rp2 for I2C and PIO.
import machine
import rp2

# Image size and bytes per pixel (depends on color mode). This example defaults
# to 320x240 with BGR565 (2 bytes per pixel).
width = 320
height = 240
bytes_per_pixel = 2

# Create the image buffer to be shared between the camera and display.
buffer = np.zeros(
    (height, width, bytes_per_pixel),
    dtype = np.uint8
)

# Verify that the buffer is located in SRAM. If it's in external PSRAM, it
# probably won't work due to the QSPI bus becoming bottlenecked by both the
# camera and display trying to access it at the same time.
SRAM_BASE = 0x20000000
SRAM_END = 0x20082000
buffer_addr = addressof(buffer)
if buffer_addr < SRAM_BASE or buffer_addr >= SRAM_END:
    raise MemoryError("Buffer is not located in SRAM")

# Initialize the DVI display, using the shared buffer.
display = dvi_rp2_hstx.DVI_HSTX(
    width = width,
    height = height,
    color_mode = dvi_rp2_hstx.DVI_HSTX.COLOR_BGR565,
    buffer = buffer,
)

# Initialize the OV5640 camera, using the shared buffer.
i2c = machine.I2C()
rp2.PIO(1).gpio_base(16)
camera = ov5640_pio.OV5640_PIO(
    i2c,
    sm_id = 5,
    pin_d0 = 28,
    pin_vsync = 42,
    pin_hsync = 41,
    pin_pclk = 40,
    pin_xclk = 44, # Optional xclock pin, specify if needed
    xclk_freq = 20_000_000,
    buffer = buffer,
    continuous = True,
)

# Open the camera to start the continuous capture process.
camera.open()
camera._capture()
