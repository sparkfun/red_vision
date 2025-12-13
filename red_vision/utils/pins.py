#-------------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# 
# Copyright (c) 2025 SparkFun Electronics
#-------------------------------------------------------------------------------
# red_vision/utils/pins.py
# 
# Red Vision Pin utility functions.
#-------------------------------------------------------------------------------

from machine import Pin

def save_pin_mode_alt(pin):
    """
    Saves the current `mode` and `alt` of the pin so it can be restored
    later. Mostly used for SPI displays on a shared SPI bus with a driver
    that needs non-SPI pin modes, such as the RP2 PIO driver. This allows
    other devices on the bus to continue using the SPI interface after the
    display driver finishes communicating with the display.

    Returns:
        tuple: (mode, alt)
    """
    # See: https://github.com/micropython/micropython/issues/17515
    # There's no way to get the mode and alt of a pin directly, so we
    # convert the pin to a string and parse it. Example formats:
    # "Pin(GPIO16, mode=OUT)"
    # "Pin(GPIO16, mode=ALT, alt=SPI)"
    pin_str = str(pin)

    # Extract the "mode" parameter from the pin string
    try:
        # Split between "mode=" and the next comma or closing parenthesis
        mode_str = pin_str[pin_str.index("mode=") + 5:].partition(",")[0].partition(")")[0]

        # Look up the mode in Pin class dictionary
        mode = Pin.__dict__[mode_str]
    except (ValueError, KeyError):
        # No mode specified, just set to -1 (default)
        mode = -1

    # Extrct the "alt" parameter from the pin string
    try:
        # Split between "alt=" and the next comma or closing parenthesis
        alt_str = pin_str[pin_str.index("alt=") + 4:].partition(",")[0].partition(")")[0]

        # Sometimes the value comes back as a number instead of a valid
        # "ALT_xyz" string, so we need to check it
        if "ALT_" + alt_str in Pin.__dict__:
            # Look up the alt in Pin class dictionary (with "ALT_" prefix)
            alt = Pin.__dict__["ALT_" + alt_str]
        else:
            # Convert the altStr to an integer
            alt = int(alt_str)
    except (ValueError, KeyError):
        # No alt specified, just set to -1 (default)
        alt = -1

    # Return the mode and alt as a tuple
    return (mode, alt)

