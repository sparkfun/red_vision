#-------------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# 
# Copyright (c) 2025 SparkFun Electronics
#-------------------------------------------------------------------------------
# red_vision/displays/st7789.py
#
# Red Vision ST7789 display driver.
# 
# This class is derived from:
# https://github.com/easytarget/st7789-framebuffer/blob/main/st7789_purefb.py
# Released under the MIT license.
# Copyright (c) 2024 Owen Carter
# Copyright (c) 2024 Ethan Lacasse
# Copyright (c) 2020-2023 Russ Hughes
# Copyright (c) 2019 Ivan Belokobylskiy
#-------------------------------------------------------------------------------

from time import sleep_ms
import struct
from ..utils import colors as rv_colors
from .video_display_driver import VideoDisplayDriver

class ST7789(VideoDisplayDriver):
    """
    Red Vision ST7789 display driver.
    """
    # ST7789 commands
    _ST7789_SWRESET = b"\x01"
    _ST7789_SLPIN = b"\x10"
    _ST7789_SLPOUT = b"\x11"
    _ST7789_NORON = b"\x13"
    _ST7789_INVOFF = b"\x20"
    _ST7789_INVON = b"\x21"
    _ST7789_DISPOFF = b"\x28"
    _ST7789_DISPON = b"\x29"
    _ST7789_CASET = b"\x2a"
    _ST7789_RASET = b"\x2b"
    _ST7789_RAMWR = b"\x2c"
    _ST7789_VSCRDEF = b"\x33"
    _ST7789_COLMOD = b"\x3a"
    _ST7789_MADCTL = b"\x36"
    _ST7789_VSCSAD = b"\x37"
    _ST7789_RAMCTL = b"\xb0"

    # MADCTL bits
    _ST7789_MADCTL_MY = 0x80
    _ST7789_MADCTL_MX = 0x40
    _ST7789_MADCTL_MV = 0x20
    _ST7789_MADCTL_ML = 0x10
    _ST7789_MADCTL_BGR = 0x08
    _ST7789_MADCTL_MH = 0x04
    _ST7789_MADCTL_RGB = 0x00

    _ENCODE_POS = ">HH"

    # Rotation indices
    ROTATION_PORTRAIT = 0
    ROTATION_LANDSCAPE = 1
    ROTATION_PORTRAIT_INVERTED = 2
    ROTATION_LANDSCAPE_INVERTED = 3

    # Rotation tables
    #   (madctl, width, height, xstart, ystart)[rotation % 4]

    _DISPLAY_240x320 = (
        (0x00, 240, 320, 0, 0),
        (0x60, 320, 240, 0, 0),
        (0xc0, 240, 320, 0, 0),
        (0xa0, 320, 240, 0, 0))

    _DISPLAY_170x320 = (
        (0x00, 170, 320, 35, 0),
        (0x60, 320, 170, 0, 35),
        (0xc0, 170, 320, 35, 0),
        (0xa0, 320, 170, 0, 35))

    _DISPLAY_240x240 = (
        (0x00, 240, 240,  0,  0),
        (0x60, 240, 240,  0,  0),
        (0xc0, 240, 240,  0, 80),
        (0xa0, 240, 240, 80,  0))

    _DISPLAY_135x240 = (
        (0x00, 135, 240, 52, 40),
        (0x60, 240, 135, 40, 53),
        (0xc0, 135, 240, 53, 40),
        (0xa0, 240, 135, 40, 52))

    _DISPLAY_128x128 = (
        (0x00, 128, 128, 2, 1),
        (0x60, 128, 128, 1, 2),
        (0xc0, 128, 128, 2, 1),
        (0xa0, 128, 128, 1, 2))

    # Supported displays (physical width, physical height, rotation table)
    _SUPPORTED_DISPLAYS = (
        (240, 320, _DISPLAY_240x320),
        (170, 320, _DISPLAY_170x320),
        (240, 240, _DISPLAY_240x240),
        (135, 240, _DISPLAY_135x240),
        (128, 128, _DISPLAY_128x128))

    # init tuple format (b'command', b'data', delay_ms)
    _ST7789_INIT_CMDS = (
        ( b'\x11', b'\x00', 120),               # Exit sleep mode
        ( b'\x13', b'\x00', 0),                 # Turn on the display
        ( b'\xb6', b'\x0a\x82', 0),             # Set display function control
        ( b'\x3a', b'\x55', 10),                # Set pixel format to 16 bits per pixel (RGB565)
        ( b'\xb2', b'\x0c\x0c\x00\x33\x33', 0), # Set porch control
        ( b'\xb7', b'\x35', 0),                 # Set gate control
        ( b'\xbb', b'\x28', 0),                 # Set VCOMS setting
        ( b'\xc0', b'\x0c', 0),                 # Set power control 1
        ( b'\xc2', b'\x01\xff', 0),             # Set power control 2
        ( b'\xc3', b'\x10', 0),                 # Set power control 3
        ( b'\xc4', b'\x20', 0),                 # Set power control 4
        ( b'\xc6', b'\x0f', 0),                 # Set VCOM control 1
        ( b'\xd0', b'\xa4\xa1', 0),             # Set power control A
                                                # Set gamma curve positive polarity
        ( b'\xe0', b'\xd0\x00\x02\x07\x0a\x28\x32\x44\x42\x06\x0e\x12\x14\x17', 0),
                                                # Set gamma curve negative polarity
        ( b'\xe1', b'\xd0\x00\x02\x07\x0a\x28\x31\x54\x47\x0e\x1c\x17\x1b\x1e', 0),
        ( b'\x21', b'\x00', 0),                 # Enable display inversion
        ( b'\x29', b'\x00', 120)                # Turn on the display
    )

    def __init__(
        self,
        interface,
        rotation = ROTATION_LANDSCAPE,
        height = None,
        width = None,
        color_mode = None,
        buffer = None,
    ):
        """
        Initializes the ST7789 display driver.

        Args:
            interface (SPI_Interface): Display interface driver
            rotation (int, optional): Orientation of display
                - ROTATION_PORTRAIT
                - ROTATION_LANDSCAPE (default)
                - ROTATION_PORTRAIT_INVERTED
                - ROTATION_LANDSCAPE_INVERTED
            height (int): Display height in pixels
            width (int): Display width in pixels
            color_mode (int, optional): Color mode to use:
                - COLOR_MODE_BGR565 (default)
            buffer (ndarray, optional): Pre-allocated image buffer
        """
        self._interface = interface
        super().__init__(height, width, color_mode, buffer)

        # Initial rotation
        self._rotation = rotation % 4

        self._interface.begin()
        # Initial dimensions and offsets; will be overridden when rotation applied
        if self._rotation % 2 == 0:
            width = self._width
            height = self._height
        else:
            width = self._height
            height = self._width
        self._xstart = 0
        self._ystart = 0
        # Check display is known and get rotation table
        self._rotations = self._find_rotations(width, height)
        if not self._rotations:
            supported_displays = ", ".join(
                [f"{display[0]}x{display[1]}" for display in self._SUPPORTED_DISPLAYS])
            raise ValueError(
                f"Unsupported {width}x{height} display. Supported displays: {supported_displays}")
        # Reset the display
        self._soft_reset()
        # Yes, send init twice, once is not always enough
        self._send_init(self._ST7789_INIT_CMDS)
        self._send_init(self._ST7789_INIT_CMDS)
        # Apply rotation
        self._set_rotation(self._rotation)

    def resolution_default(self):
        """
        Returns the default resolution for the display.

        Returns:
            tuple: (height, width) in pixels
        """
        # Use the first supported display as the default
        display = self._SUPPORTED_DISPLAYS[0]
        return (display[0], display[1])

    def resolution_is_supported(self, height, width):
        """
        Checks if the given resolution is supported by the display.

        Args:
            height (int): Height in pixels
            width (int): Width in pixels
        Returns:
            bool: True if the resolution is supported, otherwise False
        """
        return any(display[0] == height and display[1] == width for display in self._SUPPORTED_DISPLAYS)

    def color_mode_default(self):
        """
        Returns the default color mode for the display.
        """
        return rv_colors.COLOR_MODE_BGR565

    def color_mode_is_supported(self, color_mode):
        """
        Checks if the given color mode is supported by the display.

        Args:
            color_mode (int): Color mode to check
        Returns:
            bool: True if the color mode is supported, otherwise False
        """
        return color_mode == rv_colors.COLOR_MODE_BGR565

    def show(self):
        """
        Updates the display with the contents of the framebuffer.
        """
        # When sending BGR565 pixel data, the ST7789 expects each pair of bytes
        # to be sent in the opposite endianness of what the SPI peripheral would
        # normally send. So we just swap each pair of bytes.
        self._interface.write(None, self._buffer[:,:,::-1])

    def _send_init(self, commands):
        """
        Sends initialization commands to display.

        Args:
            commands (list): List of tuples (command, data, delay_ms)
        """
        for command, data, delay_ms in commands:
            self._interface.write(command, data)
            sleep_ms(delay_ms)

    def _soft_reset(self):
        """
        Sends a software reset command to the display.
        """
        self._interface.write(self._ST7789_SWRESET)
        sleep_ms(150)

    def _find_rotations(self, width, height):
        """
        Find the correct rotation for our display or returns None.

        Args:
            width (int): Display width in pixels
            height (int): Display height in pixels
        Returns:
            list: Rotation table for the display or None if not found
        """
        for display in self._SUPPORTED_DISPLAYS:
            if display[0] == width and display[1] == height:
                return display[2]
        return None

    def _set_rotation(self, rotation):
        """
        Sets display rotation.

        Args:
            rotation (int):
                - 0: Portrait
                - 1: Landscape
                - 2: Inverted portrait
                - 3: Inverted landscape
        """
        if ((rotation % 2) != (self._rotation % 2)) and (self._width != self._height):
            # non-square displays can currently only be rotated by 180 degrees
            # TODO: can framebuffer of super class be destroyed and re-created
            #       to match the new dimensions? or it's width/height changed?
            return

        # find rotation parameters and send command
        rotation %= len(self._rotations)
        (   madctl,
            self._width,
            self._height,
            self._xstart,
            self._ystart, ) = self._rotations[rotation]
        # Always BGR order for OpenCV
        madctl |= self._ST7789_MADCTL_BGR
        self._interface.write(self._ST7789_MADCTL, bytes([madctl]))
        # Set window for writing into
        self._interface.write(self._ST7789_CASET,
            struct.pack(self._ENCODE_POS, self._xstart, self._width + self._xstart - 1))
        self._interface.write(self._ST7789_RASET,
            struct.pack(self._ENCODE_POS, self._ystart, self._height + self._ystart - 1))
        self._interface.write(self._ST7789_RAMWR)
        # TODO: Can we swap (modify) framebuffer width/height in the super() class?
        self._rotation = rotation
