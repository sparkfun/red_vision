#-------------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# 
# Copyright (c) 2025 SparkFun Electronics
#-------------------------------------------------------------------------------
# red_vision/utils/video_display_driver.py
# 
# Red Vision abstract base class for display drivers.
#-------------------------------------------------------------------------------

from ..utils.video_driver import VideoDriver

class VideoDisplayDriver(VideoDriver):
    """
    Red Vision abstract base class for display drivers.
    """
    def __init__(self, *args, **kwargs):
        """
        Initializes the display driver. See VideoDriver for parameters.
        """
        super().__init__(*args, **kwargs)

    def show(self):
        """
        Updates the display with the contents of the image buffer.
        """
        raise NotImplementedError("Subclass must implement this method")
