#-------------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# 
# Copyright (c) 2025 SparkFun Electronics
#-------------------------------------------------------------------------------
# red_vision/displays/spi_generic.py
#
# Red Vision SPI display driver using a generic SPI interface.
# 
# This class is derived from:
# https://github.com/easytarget/st7789-framebuffer/blob/main/st7789_purefb.py
# Released under the MIT license.
# Copyright (c) 2024 Owen Carter
# Copyright (c) 2024 Ethan Lacasse
# Copyright (c) 2020-2023 Russ Hughes
# Copyright (c) 2019 Ivan Belokobylskiy
#-------------------------------------------------------------------------------

from machine import Pin
from ..utils.pins import save_pin_mode_alt

class SPI_Generic():
    """
    Red Vision SPI display driver using a generic SPI interface.
    """
    def __init__(
        self,
        spi,
        pin_dc,
        pin_cs=None,
    ):
        """
        Initializes the ST7789 SPI display driver.

        Args:
            width (int): Display width in pixels
            height (int): Display height in pixels
            spi (SPI): SPI bus object
            pin_dc (int): Data/Command pin number
            pin_cs (int, optional): Chip Select pin number
            rotation (int, optional): Orientation of display
              - 0: Portrait (default)
              - 1: Landscape
              - 2: Inverted portrait
              - 3: Inverted landscape
            bgr_order (bool, optional): Color order
              - True: BGR (default)
              - False: RGB
            reverse_bytes_in_word (bool, optional):
              - Enable if the display uses LSB byte order for color words
        """
        # Store SPI arguments
        self._spi = spi
        self._dc = Pin(pin_dc) # Don't change mode/alt
        self._cs = Pin(pin_cs, Pin.OUT, value=1) if pin_cs else None

    def begin(self):
        """
        Initializes the SPI interface for the display.
        """
        # Nothing to do for SPI
        pass

    def write(self, command=None, data=None):
        """
        Writes commands and data to the display.

        Args:
            command (bytes, optional): Command to send to the display
            data (bytes, optional): Data to send to the display
        """
        # Save the current mode and alt of the DC pin in case it's used by
        # another device on the same SPI bus
        dcMode, dcAlt = save_pin_mode_alt(self._dc)

        # Temporarily set the DC pin to output mode
        self._dc.init(mode=Pin.OUT)

        # Write to the display
        if self._cs:
            self._cs.off()
        if command is not None:
            self._dc.off()
            self._spi.write(command)
        if data is not None:
            self._dc.on()
            self._spi.write(data)
        if self._cs:
            self._cs.on()

        # Restore the DC pin to its original mode and alt
        self._dc.init(mode=dcMode, alt=dcAlt)
