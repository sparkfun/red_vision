# Imports.
import cv2 as cv
from ulab import numpy as np
from red_vision.displays import dvi_rp2_hstx

# Image size.
width = 320
height = 240

# Create a DVI_HSTX display instance.
display = dvi_rp2_hstx.DVI_HSTX(
    width = width,
    height = height,
    # color_mode = dvi_rp2_hstx.DVI_HSTX.COLOR_BGR233,
    # color_mode = dvi_rp2_hstx.DVI_HSTX.COLOR_GRAY8,
    color_mode = dvi_rp2_hstx.DVI_HSTX.COLOR_BGR565,
    # color_mode = dvi_rp2_hstx.DVI_HSTX.COLOR_BGRA8888,
)

# OpenCV doesn't have a BGR233 color conversion, so if we're using that mode,
# we need to create our test image with single channel values.
if display._color_mode == dvi_rp2_hstx.DVI_HSTX.COLOR_BGR233:
    image_channels = 1
    color_r = (0xE0)
    color_g = (0x1C)
    color_b = (0x03)
    color_y = (0xFC)
    color_c = (0x1F)
    color_m = (0xE3)
    color_w = (0xFF)
    color_gray = (0x92)
    color_blk = (0x00)
else:
    image_channels = 3
    color_r = (0, 0, 255)
    color_g = (0, 255, 0)
    color_b = (255, 0, 0)
    color_y = (0, 255, 255)
    color_c = (255, 255, 0)
    color_m = (255, 0, 255)
    color_w = (255, 255, 255)
    color_gray = (128, 128, 128)
    color_blk = (0, 0, 0)

# Test image.
orig = np.zeros((height, width, image_channels), dtype=np.uint8)
orig[:, :] = color_gray
orig[ 0:10, 0:10] = color_r
orig[10:20, 0:10] = color_g
orig[20:30, 0:10] = color_b
orig[00:10,10:20] = color_y
orig[10:20,10:20] = color_c
orig[20:30,10:20] = color_m
orig[ 0:30,20:30] = color_w
orig = cv.ellipse(orig, (160, 120), (100, 50), 0, 0, 360, color_blk, -1)
orig = cv.putText(orig, "Hello DVI!", (80, 200), cv.FONT_HERSHEY_SIMPLEX, 1, color_w, 2)
orig = cv.putText(orig, "Red!", (20, 60), cv.FONT_HERSHEY_SIMPLEX, 1, color_r, 2)
orig = cv.putText(orig, "Green!", (100, 60), cv.FONT_HERSHEY_SIMPLEX, 1, color_g, 2)
orig = cv.putText(orig, "Blue!", (220, 60), cv.FONT_HERSHEY_SIMPLEX, 1, color_b, 2)

# Show test image.
display.imshow(orig)

# Draw a color gradient test pattern directly into the display buffer.
for i in range(256):
    display._buffer[0:10, width - 256 + i] = i

# When writing the display buffer directly, if the buffer is in PSRAM, some
# pixels don't update until a garbage collection cycle occurs. Not sure why...
if display._buffer_is_in_psram:
    import gc
    gc.collect()
