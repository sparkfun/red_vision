#-------------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# 
# Copyright (c) 2025 SparkFun Electronics
#-------------------------------------------------------------------------------
# red_vision/utils/memory.py
# 
# Red Vision memory utility functions.
#-------------------------------------------------------------------------------

import sys
import machine
import uctypes

def is_in_internal_ram(address):
    """
    Checks whether a given object or memory address is in internal RAM.
    """
    # Get the memory address if an object is given.
    if type(address) is not int:
        address = uctypes.addressof(address)

    if "rp2" in sys.platform:
        # SRAM address range.
        SRAM_BASE = 0x20000000
        SRAM_END = 0x20082000
        
        # Return whether address is in SRAM.
        return address >= SRAM_BASE and address < SRAM_END
    else:
        raise NotImplementedError("Not implemented for this platform.")

def is_in_external_ram(address):
    """
    Checks whether a given object or memory address is in external RAM.
    """
    return not is_in_internal_ram(address)

def external_ram_max_bytes_per_second():
    """
    Estimates the maximum bytes per second for external RAM access.
    """
    if "rp2" in sys.platform:
        # PSRAM timing register parameters.
        XIP_QMI_BASE = 0x400D0000
        M1_TIMING = XIP_QMI_BASE + 0x20
        CLKDIV_MASK = 0xFF

        # Get PSRAM clock divider, typically 2.
        psram_clk_div = machine.mem32[M1_TIMING] & CLKDIV_MASK

        # Compute PSRAM pixel transfer rate. PSRAM is on the QSPI bus, which
        # transfers 1 byte every 2 clock cycles.
        psram_clock_hz = machine.freq() / psram_clk_div # Typically 75 MHz
        psram_bytes_per_second = psram_clock_hz / 2 # Typically 37.5 MBps

        # Probing with an oscilloscope has shown that the XIP stream typically
        # performs transfers in 32 bit bursts every 19 system clock cycles
        # (~127ns) instead of the nominal 16 system clock cycles (~107ns). We'll
        # include it as a safety margin.
        psram_bytes_per_second *= 16 / 19 # Typically 31.5 MBps

        # Return the estimated PSRAM bytes per second.
        return psram_bytes_per_second
    else:
        raise NotImplementedError("Not implemented for this platform.")
