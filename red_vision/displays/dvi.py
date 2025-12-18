#-------------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# 
# Copyright (c) 2025 SparkFun Electronics
#-------------------------------------------------------------------------------
# red_vision/displays/dvi.py
#
# Red Vision DVI display driver.
#-------------------------------------------------------------------------------

from .video_display_driver import VideoDisplayDriver

class DVI(VideoDisplayDriver):
    """
    Red Vision DVI display driver.
    """
    def __init__(
        self,
        interface,
        height = None,
        width = None,
        color_mode = None,
        buffer = None,
    ):
        """
        Initializes the DVI display driver.

        Args:
            width (int): Display width in pixels
            height (int): Display height in pixels
            color_mode (int, optional): Color mode
              - COLOR_BGR233
              - COLOR_GRAY8
              - COLOR_BGR565 (default)
              - COLOR_BGRA8888
            buffer (ndarray, optional): Pre-allocated frame buffer.
        """
        # Store parameters
        self._interface = interface

        # Initialize the base display class
        super().__init__(height, width, color_mode, buffer)

        # Begin the interface driver
        self._interface.begin(
            self._buffer,
            self._color_mode,
        )

    def resolution_default(self):
        """
        Returns the default resolution for the display.

        Returns:
            tuple: (height, width) in pixels
        """
        return self._interface.resolution_default()

    def resolution_is_supported(self, height, width):
        """
        Checks if the given resolution is supported by the display.

        Args:
            height (int): Height in pixels
            width (int): Width in pixels
        Returns:
            bool: True if the resolution is supported, otherwise False
        """
        return self._interface.resolution_is_supported(height, width)

    def color_mode_default(self):
        """
        Returns the default color mode for the display.
        """
        return self._interface.color_mode_default()

    def color_mode_is_supported(self, color_mode):
        """
        Checks if the given color mode is supported by the display.

        Args:
            color_mode (int): Color mode to check
        Returns:
            bool: True if the color mode is supported, otherwise False
        """
        return self._interface.color_mode_is_supported(color_mode)

    def show(self):
        """
        Updates the display with the contents of the framebuffer.
        """
        pass
