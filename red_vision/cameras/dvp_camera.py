#-------------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# 
# Copyright (c) 2025 SparkFun Electronics
#-------------------------------------------------------------------------------
# red_vision/cameras/dvp_camera.py
# 
# Red Vision abstract base class for DVP (Digital Video Port) camera drivers.
#-------------------------------------------------------------------------------

from .video_capture_driver import VideoCaptureDriver

class DVP_Camera(VideoCaptureDriver):
    """
    Red Vision abstract base class for DVP (Digital Video Port) camera drivers.
    """
    def __init__(
        self,
        i2c,
        i2c_address,
        height = None,
        width = None,
        color_mode = None,
        buffer = None,
    ):
        """
        Initializes the DVP camera with I2C communication.

        Args:
            i2c (I2C): I2C object for communication
            i2c_address (int): I2C address of the camera
            height (int, optional): Image height in pixels
            width (int, optional): Image width in pixels
            color_mode (int, optional): Color mode to use
            buffer (ndarray, optional): Pre-allocated image buffer
        """
        # Store I2C parameters.
        self._i2c = i2c
        self._i2c_address = i2c_address

        # Initialize the base VideoCaptureDriver class
        super().__init__(height, width, color_mode, buffer)

    def _read_register(self, reg, nbytes=1):
        """
        Reads a register(s) from the camera over I2C.

        Args:
            reg (int): Start register address to read
            nbytes (int, optional): Number of bytes to read from the register
                (default: 1)

        Returns:
            bytes: Data read from the register
        """
        self._i2c.writeto(self._i2c_address, bytes([reg >> 8, reg & 0xFF]))
        return self._i2c.readfrom(self._i2c_address, nbytes)

    def _write_register(self, reg, data):
        """
        Writes data to a register(s) on the camera over I2C.

        Args:
            reg (int): Start register address to write
            data (bytes, int, list, tuple): Data to write to the register(s)
        """
        if isinstance(data, int):
            data = bytes([data])
        elif isinstance(data, (list, tuple)):
            data = bytes(data)
        self._i2c.writeto(self._i2c_address, bytes([reg >> 8, reg & 0xFF]) + data)
