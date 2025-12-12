#-------------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# 
# Copyright (c) 2025 SparkFun Electronics
#-------------------------------------------------------------------------------
# red_vision/cameras/video_capture.py
# 
# Red Vision generic camera class. This is implemented like standard OpenCV's
# VideoCapture class.
#-------------------------------------------------------------------------------

import cv2
from ..utils import colors as rv_colors

class VideoCapture():
    """
    Red Vision generic camera class. This is implemented like standard OpenCV's
    VideoCapture class.
    """
    def __init__(
            self,
            driver,
            ):
        """
        Initializes the camera.
        """
        # Store driver reference.
        self._driver = driver

    def open(self):
        """
        Opens the camera and prepares it for capturing images.
        """
        self._driver.open()

    def release(self):
        """
        Releases the camera and frees any resources.
        """
        self._driver.release()

    def grab(self):
        """
        Grabs a single frame from the camera.

        Returns:
            bool: True if the frame was grabbed successfully, otherwise False
        """
        return self._driver.grab()

    def retrieve(self, image = None):
        """
        Retrieves the most recently grabbed frame from the camera.

        Args:
            image (ndarray, optional): Image to retrieve into
        Returns:
            tuple: (success, image)
                - success (bool): True if the image was retrieved, otherwise False
                - image (ndarray): The retrieved image, or None if retrieval failed
        """
        color_mode = self._driver.color_mode()
        buffer = self._driver.buffer()
        if (color_mode == rv_colors.COLOR_MODE_BGR888 or
                color_mode == rv_colors.COLOR_MODE_GRAY8 or
                color_mode == rv_colors.COLOR_MODE_BGR233): # No conversion available
            # These color modes are copied directly with no conversion.
            if image is not None:
                # Copy buffer to provided image.
                image[:] = buffer
                return (True, image)
            else:
                # Return a copy of the buffer.
                return (True, buffer.copy())
        elif color_mode == rv_colors.COLOR_MODE_BAYER_BG:
            return (True, cv2.cvtColor(buffer, cv2.COLOR_BayerBG2BGR, image))
        elif color_mode == rv_colors.COLOR_MODE_BAYER_GB:
            return (True, cv2.cvtColor(buffer, cv2.COLOR_BayerGB2BGR, image))
        elif color_mode == rv_colors.COLOR_MODE_BAYER_RG:
            return (True, cv2.cvtColor(buffer, cv2.COLOR_BayerRG2BGR, image))
        elif color_mode == rv_colors.COLOR_MODE_BAYER_GR:
            return (True, cv2.cvtColor(buffer, cv2.COLOR_BayerGR2BGR, image))
        elif color_mode == rv_colors.COLOR_MODE_BGR565:
            return (True, cv2.cvtColor(buffer, cv2.COLOR_BGR5652BGR, image))
        elif color_mode == rv_colors.COLOR_MODE_BGRA8888:
            return (True, cv2.cvtColor(buffer, cv2.COLOR_BGRA2BGR, image))
        else:
            NotImplementedError("Unsupported color mode")

    def read(self, image = None):
        """
        Reads an image from the camera.

        Args:
            image (ndarray, optional): Image to read into

        Returns:
            tuple: (success, image)
                - success (bool): True if the image was read, otherwise False
                - image (ndarray): The captured image, or None if reading failed
        """
        if not self.grab():
            return (False, None)
        return self.retrieve(image = image)
