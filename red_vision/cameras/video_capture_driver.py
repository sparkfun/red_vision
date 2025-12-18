#-------------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# 
# Copyright (c) 2025 SparkFun Electronics
#-------------------------------------------------------------------------------
# red_vision/utils/video_capture_driver.py
# 
# Red Vision abstract base class for camera drivers.
#-------------------------------------------------------------------------------

from ..utils.video_driver import VideoDriver

class VideoCaptureDriver(VideoDriver):
    """
    Red Vision abstract base class for camera drivers.
    """
    def __init__(self, *args, **kwargs):
        """
        Initializes the camera driver. See VideoDriver for parameters.
        """
        super().__init__(*args, **kwargs)

    def open(self):
        """
        Opens the camera and prepares it for capturing images.
        """
        raise NotImplementedError("Subclass must implement this method")

    def release(self):
        """
        Releases the camera and frees any resources.
        """
        raise NotImplementedError("Subclass must implement this method")

    def grab(self):
        """
        Grabs a single frame from the camera.

        Returns:
            bool: True if the frame was grabbed successfully, otherwise False
        """
        raise NotImplementedError("Subclass must implement this method")
