#-------------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# 
# Copyright (c) 2025 SparkFun Electronics
#-------------------------------------------------------------------------------
# red_vision/utils/video_driver.py
# 
# Red Vision abstract base class for camera and display drivers.
#-------------------------------------------------------------------------------

from ulab import numpy as np
from . import colors

class VideoDriver():
    """
    Red Vision abstract base class for camera and display drivers.
    """
    def __init__(
            self,
            height = None,
            width = None,
            color_mode = None,
            buffer = None,
            ):
        """
        Initializes the camera.
        """
        # Determine image resolution.
        if height is None or width is None:
            # Use the driver's default resolution.
            self._height, self._width = self.resolution_default()
        else:
            # Check if the driver supports the requested resolution.
            if not self.resolution_is_supported(height, width):
                raise ValueError("Unsupported resolution")
            
            # Store the resolution.
            self._height = height
            self._width = width

        # Determine color mode.
        if color_mode is None:
            # Use the driver's default color mode.
            self._color_mode = self.color_mode_default()
        else:
            # Check if the driver supports the requested color mode.
            if not self.color_mode_is_supported(color_mode):
                raise ValueError("Unsupported color mode")

            # Store the color mode.            
            self._color_mode = color_mode

        # Create or store the image buffer.
        self._bytes_per_pixel = colors.bytes_per_pixel(self._color_mode)
        buffer_shape = (self._height, self._width, self._bytes_per_pixel)
        if buffer is None:
            # No buffer provided, create a new one.
            self._buffer = np.zeros(buffer_shape, dtype=np.uint8)
        else:
            # Use the provided buffer, formatted as a NumPy ndarray.
            self._buffer = np.frombuffer(buffer, dtype=np.uint8)

            # Reshape to the provided dimensions.
            self._buffer = self._buffer.reshape(buffer_shape)

    def buffer(self):
        """
        Returns the framebuffer used by the display.

        Returns:
            ndarray: Framebuffer
        """
        return self._buffer

    def color_mode(self):
        """
        Returns the current color mode of the display.
        """
        return self._color_mode

    def resolution_default():
        """
        Returns the default resolution of the camera.

        Returns:
            tuple: (height, width)
        """
        raise NotImplementedError("Subclass must implement this method")

    def resolution_is_supported():
        """
        Returns whether the given resolution is supported by the camera.

        Args:
            height (int): Image height
            width (int): Image width
        Returns:
            bool: True if supported, False otherwise
        """
        raise NotImplementedError("Subclass must implement this method")

    def color_mode_default():
        """
        Returns the default color mode of the camera.

        Returns:
            int: Color mode
        """
        raise NotImplementedError("Subclass must implement this method")

    def color_mode_is_supported():
        """
        Returns the default resolution of the camera.

        Returns:
            tuple: (height, width)
        """
        raise NotImplementedError("Subclass must implement this method")
