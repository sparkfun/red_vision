#-------------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# 
# Copyright (c) 2025 SparkFun Electronics
#-------------------------------------------------------------------------------
# red_vision/displays/video_display.py
# 
# Red Vision generic display class. This is to be used with `cv.imshow()` in
# place of the window name string used by standard OpenCV.
#-------------------------------------------------------------------------------

import cv2 as cv
from ulab import numpy as np
from ..utils import colors as rv_colors

class VideoDisplay():
    """
    Red Vision generic display class. This is to be used with `cv.imshow()` in
    place of the window name string used by standard OpenCV.
    """
    def __init__(
            self,
            driver,
            ):
        """
        Initializes a VideoDisplay object with the provided driver.

        Args:
            driver (VideoDisplayDriver): Display driver to use
        """
        # Store driver reference.
        self._driver = driver

    def imshow(self, image):
        """
        Shows a NumPy image on the display.

        Args:
            image (ndarray): Image to show
        """
        # Get the common ROI between the image and internal display buffer.
        image_roi, buffer_roi = self._get_common_roi_with_buffer(image)

        # Ensure the image is in uint8 format
        image_roi = self._convert_to_uint8(image_roi)

        # Convert the image to current format and write it to the buffer.
        color_mode = self._driver.color_mode()
        if (color_mode == rv_colors.COLOR_MODE_GRAY8 or
                # No conversion available for the modes below, treat as GRAY8
                color_mode == rv_colors.COLOR_MODE_BAYER_BG or
                color_mode == rv_colors.COLOR_MODE_BAYER_GB or
                color_mode == rv_colors.COLOR_MODE_BAYER_RG or
                color_mode == rv_colors.COLOR_MODE_BAYER_GR or
                color_mode == rv_colors.COLOR_MODE_BGR233):
            self._convert_to_gray8(image_roi, buffer_roi)
        elif color_mode == rv_colors.COLOR_MODE_BGR565:
            self._convert_to_bgr565(image_roi, buffer_roi)
        elif color_mode == rv_colors.COLOR_MODE_BGR888:
            self._convert_to_bgr888(image_roi, buffer_roi)
        elif color_mode == rv_colors.COLOR_MODE_BGRA8888:
            self._convert_to_bgra8888(image_roi, buffer_roi)
        else:
            raise ValueError("Unsupported color mode")

        # Show the buffer on the display.
        self._driver.show()

    def clear(self):
        """
        Clears the display by filling it with black color.
        """
        self._driver.buffer()[:] = 0
        self._driver.show()

    def splash(self, filename="splash.png"):
        """
        Shows a splash image on the display if one is available, otherwise
        clears the display of any previous content.

        Args:
            filename (str, optional): Path to a splash image file. Defaults to
                            "splash.png"
        """
        try:
            # Attempt to load and show the splash image
            self.imshow(cv.imread(filename))
        except Exception:
            # Couldn't load the image, just clear the display as a fallback
            self.clear()

    def _get_common_roi_with_buffer(self, image):
        """
        Gets the common region of interest (ROI) between the image and the 
        display's internal buffer.

        Args:
            image (ndarray): Image to display
        
        Returns:
            tuple: (image_roi, buffer_roi)
                - image_roi (ndarray): ROI of the image
                - buffer_roi (ndarray): ROI of the display's buffer
        """
        # Ensure image is a NumPy ndarray
        if type(image) is not np.ndarray:
            raise TypeError("Image must be a NumPy ndarray")
        
        # Determing number of rows and columns in the image
        image_rows = image.shape[0]
        if image.ndim < 2:
            image_cols = 1
        else:
            image_cols = image.shape[1]
        
        # Get the common ROI between the image and the buffer
        buffer = self._driver.buffer()
        row_max = min(image_rows, buffer.shape[0])
        col_max = min(image_cols, buffer.shape[1])
        img_roi = image[:row_max, :col_max]
        buffer_roi = buffer[:row_max, :col_max]
        return img_roi, buffer_roi

    def _convert_to_uint8(self, image):
        """
        Converts the image to uint8 format if necessary.

        Args:
            image (ndarray): Image to convert

        Returns:
            Image: Converted image
        """
        # Check if the image is already in uint8 format
        if image.dtype is np.uint8:
            return image
        
        # Convert to uint8 format. This unfortunately requires creating a new
        # buffer for the converted image, which takes more memory
        if image.dtype == np.int8:
            return cv.convertScaleAbs(image, alpha=1, beta=127)
        elif image.dtype == np.int16:
            return cv.convertScaleAbs(image, alpha=1/255, beta=127)
        elif image.dtype == np.uint16:
            return cv.convertScaleAbs(image, alpha=1/255)
        elif image.dtype == np.float:
            # This implementation creates an additional buffer from np.clip()
            # TODO: Find another solution that avoids an additional buffer
            return cv.convertScaleAbs(np.clip(image, 0, 1), alpha=255)
        else:
            raise ValueError(f"Unsupported image dtype: {image.dtype}")

    def _convert_to_gray8(self, src, dst):
        """
        Converts an image to GRAY8 format.

        Args:
            src (ndarray): Input image
            dst (ndarray): Output GRAY8 buffer
        """
        # Determine the number of channels in the image
        if src.ndim < 3:
            ch = 1
        else:
            ch = src.shape[2]

        # Convert the image to GRAY8 format based on the number of channels
        if ch == 1: # GRAY8
            # Already in GRAY8 format
            # For some reason, this is relatively slow and creates a new buffer:
            # https://github.com/v923z/micropython-ulab/issues/726
            dst[:] = src.reshape(dst.shape)
        elif ch == 2: # BGR565
            dst = cv.cvtColor(src, cv.COLOR_BGR5652GRAY, dst)
        elif ch == 3: # BGR888
            dst = cv.cvtColor(src, cv.COLOR_BGR2GRAY, dst)
        elif ch == 4: # BGRA8888
            dst = cv.cvtColor(src, cv.COLOR_BGRA2GRAY, dst)
        else:
            raise ValueError("Unsupported number of channels in source image")

    def _convert_to_bgr565(self, src, dst):
        """
        Converts an image to BGR565 format.

        Args:
            src (ndarray): Input image
            dst (ndarray): Output BGR565 buffer
        """
        # Determine the number of channels in the image
        if src.ndim < 3:
            ch = 1
        else:
            ch = src.shape[2]

        # Convert the image to BGR565 format based on the number of channels
        if ch == 1: # GRAY8
            dst = cv.cvtColor(src, cv.COLOR_GRAY2BGR565, dst)
        elif ch == 2: # BGR565
            # Already in BGR565 format
            # For some reason, this is relatively slow and creates a new buffer:
            # https://github.com/v923z/micropython-ulab/issues/726
            dst[:] = src.reshape(dst.shape)
        elif ch == 3: # BGR888
            dst = cv.cvtColor(src, cv.COLOR_BGR2BGR565, dst)
        elif ch == 4: # BGRA8888
            dst = cv.cvtColor(src, cv.COLOR_BGRA2BGR565, dst)
        else:
            raise ValueError("Unsupported number of channels in source image")

    def _convert_to_bgr888(self, src, dst):
        """
        Converts an image to BGR888 format.

        Args:
            src (ndarray): Input image
            dst (ndarray): Output BGR888 buffer
        """
        # Determine the number of channels in the image
        if src.ndim < 3:
            ch = 1
        else:
            ch = src.shape[2]

        # Convert the image to BGR888 format based on the number of channels
        if ch == 1: # GRAY8
            dst = cv.cvtColor(src, cv.COLOR_GRAY2BGR, dst)
        elif ch == 2: # BGR565
            dst = cv.cvtColor(src, cv.COLOR_BGR5652BGR, dst)
        elif ch == 3: # BGR888
            # Already in BGR888 format
            # For some reason, this is relatively slow and creates a new buffer:
            # https://github.com/v923z/micropython-ulab/issues/726
            dst[:] = src.reshape(dst.shape)
        elif ch == 4: # BGRA8888
            dst = cv.cvtColor(src, cv.COLOR_BGRA2BGR, dst)
        else:
            raise ValueError("Unsupported number of channels in source image")

    def _convert_to_bgra8888(self, src, dst):
        """
        Converts an image to BGRA8888 format.

        Args:
            src (ndarray): Input image
            dst (ndarray): Output BGRA8888 buffer
        """
        # Determine the number of channels in the image
        if src.ndim < 3:
            ch = 1
        else:
            ch = src.shape[2]

        # Convert the image to BGRA8888 format based on the number of channels
        if ch == 1: # GRAY8
            dst = cv.cvtColor(src, cv.COLOR_GRAY2BGRA, dst)
        elif ch == 2: # BGR565
            dst = cv.cvtColor(src, cv.COLOR_BGR5652BGRA, dst)
        elif ch == 3: # BGR888
            dst = cv.cvtColor(src, cv.COLOR_BGR2BGRA, dst)
        elif ch == 4: # BGRA8888
            # Already in BGRA8888 format
            # For some reason, this is relatively slow and creates a new buffer:
            # https://github.com/v923z/micropython-ulab/issues/726
            dst[:] = src.reshape(dst.shape)
        else:
            raise ValueError("Unsupported number of channels in source image")
