#-------------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# 
# Copyright (c) 2025 SparkFun Electronics
#-------------------------------------------------------------------------------
# red_vision/utils/colors.py
# 
# Red Vision color mode constants and utility functions.
#-------------------------------------------------------------------------------

# Color mode constants.
COLOR_MODE_BAYER_BG = 0
COLOR_MODE_BAYER_GB = 1
COLOR_MODE_BAYER_RG = 2
COLOR_MODE_BAYER_GR = 3
COLOR_MODE_GRAY8 = 4
COLOR_MODE_BGR233 = 5
COLOR_MODE_BGR565 = 6
COLOR_MODE_BGR888 = 7
COLOR_MODE_BGRA8888 = 8

def bytes_per_pixel(color_mode):
    """
    Returns the number of bytes per pixel for the given color mode.
    """
    if (color_mode == COLOR_MODE_BAYER_BG or
            color_mode == COLOR_MODE_BAYER_GB or
            color_mode == COLOR_MODE_BAYER_RG or
            color_mode == COLOR_MODE_BAYER_GR or
            color_mode == COLOR_MODE_GRAY8 or
            color_mode == COLOR_MODE_BGR233):
        return 1
    elif color_mode == COLOR_MODE_BGR565:
        return 2
    elif color_mode == COLOR_MODE_BGR888:
        return 3
    elif color_mode == COLOR_MODE_BGRA8888:
        return 4
    else:
        raise ValueError("Unsupported color mode")
