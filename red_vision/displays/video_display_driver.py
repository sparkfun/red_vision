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
    def show(self):
        """
        Updates the display with the contents of the framebuffer.
        """
        raise NotImplementedError("Subclass must implement this method")
