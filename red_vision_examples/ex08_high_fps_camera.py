#-------------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# 
# Copyright (c) 2025 SparkFun Electronics
#-------------------------------------------------------------------------------
# red_vision_examples/ex08_high_fps_camera.py
# 
# This example demsontrates how to show a high frame rate camera stream on a
# display by having the display and camera drivers share the same image buffer.
# This only works with cameras and displays that support the exact same
# resolutions and color formats. Because no color space conversions are needed,
# very little (or even zero) processing is required. And because no data copying
# is needed, the max frame rate of the camera or display (whichever is lower)
# can be achieved.
# 
# Note that it's impossible to show any other images on the display while the
# camera is capturing images. To show other images, you either have to release
# the camera, or use a second display.
#-------------------------------------------------------------------------------

# This example does not use the `rv_init` module, in order to demonstrate some
# more advanced features. The initialization is done directly in this example.
import red_vision as rv

# Import OpenCV.
import cv2 as cv

# Import NumPy.
from ulab import numpy as np

# Import the Pin class for the board's default pins, as well as SPI and I2C.
from machine import Pin, SPI, I2C

# When the Red Vision Kit for RedBoard is used with the IoT RedBoard RP2350,
# both the display and camera use GPIO 16-47 instead of GPIO 0-31, so we need to
# adjust the base GPIO for PIO drivers.
import sys
if "IoT RedBoard RP2350" in sys.implementation._machine:
    import rp2
    rp2.PIO(1).gpio_base(16)

# Image size and bytes per pixel (depends on color mode). This example defaults
# to 320x240 with BGR565.
height = 240
width = 320
color_mode = rv.colors.COLOR_MODE_BGR565
bytes_per_pixel = rv.colors.bytes_per_pixel(color_mode)

# Create the image buffer to be shared between the camera and display.
shared_buffer = np.zeros(
    (height, width, bytes_per_pixel),
    dtype = np.uint8
)

# Verify that the buffer is located in SRAM. If it's in external PSRAM, it
# probably won't work due to the QSPI bus becoming bottlenecked by both the
# camera and display trying to access it at the same time.
if rv.utils.memory.is_in_external_ram(shared_buffer):
    raise MemoryError("Buffer must be in internal RAM for this example")

# Set up and initialize a display. This example uses the ST7789, but you can
# change this to use any camera and display that support the same resolution and
# color format. SPI is used here for compatibility with most platforms, but
# other interfaces can be faster.
interface_display = rv.displays.SPI_Generic(
    spi = SPI(
        baudrate = 24_000_000,
    ),
    pin_dc = Pin.board.DISPLAY_DC,
    pin_cs = Pin.board.DISPLAY_CS,
)
driver_display = rv.displays.ST7789(
    interface = interface_display,
    height = height,
    width = width,
    color_mode = color_mode,
    buffer = shared_buffer, # Use the shared image buffer.
)
display = rv.displays.VideoDisplay(driver_display)

# Set up and initialize a camera. This example uses the OV5640, but you can
# change this to use any camera and display that support the same resolution and
# color format.
interface_camera = rv.cameras.DVP_RP2_PIO(
    sm_id = 5,
    pin_d0 = Pin.board.CAMERA_D0,
    pin_vsync = Pin.board.CAMERA_VSYNC,
    pin_hsync = Pin.board.CAMERA_HSYNC,
    pin_pclk = Pin.board.CAMERA_PCLK,
    pin_xclk = Pin.board.CAMERA_XCLK, # Specify the XCLK pin if needed.
)
driver_camera = rv.cameras.OV5640(
    interface = interface_camera,
    i2c = I2C(),
    continuous = True, # Continuous capture mode for fastest frame rate.
    height = height,
    width = width,
    color_mode = color_mode,
    buffer = shared_buffer, # Use the shared image buffer.
)
camera = rv.cameras.VideoCapture(driver_camera)

# Open the camera. When continuous mode is enabled, the camera driver will
# automatically start capturing frames in the background and repeatedly filling
# the shared image buffer with new frames, no need to call read().
camera.open()

# Prompt the user to press a key to continue.
print("Press any key to continue")

while True:
    # With some display drivers (eg. ST7789), show() must be called to update
    # the display with the contents of the image buffer. For other drivers
    # (eg. DVI), the display is continuously updated in the background, so
    # calling show() is not necessary.
    driver_display.show()

    # Check for key presses.
    key = cv.waitKey(1)

    # If any key is pressed, exit the loop.
    if key != -1:
        break

# Release the camera
camera.release()
