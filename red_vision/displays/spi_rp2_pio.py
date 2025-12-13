#-------------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# 
# Copyright (c) 2025 SparkFun Electronics
#-------------------------------------------------------------------------------
# red_vision/displays/spi_rp2_pio.py
#
# Red Vision SPI display driver using a PIO interface. Only available on
# Raspberry Pi RP2 processors.
# 
# This class is derived from:
# https://github.com/raspberrypi/pico-examples/tree/master/pio/st7789_lcd
# Released under the MIT license.
# Copyright (c) 2024 Owen Carter
# Copyright (c) 2024 Ethan Lacasse
# Copyright (c) 2020-2023 Russ Hughes
# Copyright (c) 2019 Ivan Belokobylskiy
#-------------------------------------------------------------------------------

import rp2
from machine import Pin
from ..utils.pins import save_pin_mode_alt

class SPI_RP2_PIO():
    """
    Red Vision SPI display driver using a PIO interface. Only available on
    Raspberry Pi RP2 processors.
    """
    def __init__(
        self,
        sm_id,
        pin_clk,
        pin_tx,
        pin_dc,
        pin_cs=None,
        freq=-1,
    ):
        """
        Initializes the ST7789 PIO display driver.

        Args:
            sm_id (int): PIO state machine ID
            pin_clk (int): Clock pin number
            pin_tx (int): Data pin number
            pin_dc (int): Data/Command pin number
            pin_cs (int, optional): Chip Select pin number
            freq (int, optional): Frequency in Hz for the PIO state machine.
                Default is -1, which uses the system clock frequency
        """
        # Store PIO arguments
        self._sm_id = sm_id
        self._clk = Pin(pin_clk) # Don't change mode/alt
        self._tx = Pin(pin_tx) # Don't change mode/alt
        self._dc = Pin(pin_dc) # Don't change mode/alt
        self._cs = Pin(pin_cs, Pin.OUT, value=1) if pin_cs else None
        self._freq = freq

    def begin(self):
        """
        Initializes the PIO interface for the display.
        """

        # Get the current mode and alt of the pins so they can be restored
        txMode, txAlt = save_pin_mode_alt(self._tx)
        clkMode, clkAlt = save_pin_mode_alt(self._clk)

        # Initialize the PIO state machine
        self._sm = rp2.StateMachine(
            self._sm_id,
            self._pio_write_spi,
            freq = self._freq,
            out_base = self._tx,
            sideset_base = self._clk,
            pull_thresh = 8 # 8 bits per transfer
        )

        # The tx and clk pins just got their mode and alt set for PIO0 or PIO1.
        # We need to save them again to restore later when write() is called,
        # if we haven't already
        if not hasattr(self, '_txMode'):
            self._txMode, self._txAlt = save_pin_mode_alt(self._tx)
            self._clkMode, self._clkAlt = save_pin_mode_alt(self._clk)

        # Now restore the original mode and alt of the pins
        self._tx.init(mode=txMode, alt=txAlt)
        self._clk.init(mode=clkMode, alt=clkAlt)

        # Instantiate a DMA controller if not already done
        if not hasattr(self, '_dma'):
            self._dma = rp2.DMA()

        # Configure up DMA to write to the PIO state machine
        req_num = ((self._sm_id // 4) << 3) + (self._sm_id % 4)
        dma_ctrl = self._dma.pack_ctrl(
            size = 0,
            inc_write = False,
            treq_sel = req_num,
        )
        self._dma.config(
            write = self._sm,
            ctrl = dma_ctrl
        )

    def write(self, command=None, data=None):
        """
        Writes commands and data to the display.

        Args:
            command (bytes, optional): Command to send to the display
            data (bytes, optional): Data to send to the display
        """
        # Save the current mode and alt of the spi pins in case they're used by
        # another device on the same SPI bus
        dcMode, dcAlt = save_pin_mode_alt(self._dc)
        txMode, txAlt = save_pin_mode_alt(self._tx)
        clkMode, clkAlt = save_pin_mode_alt(self._clk)

        # Temporarily set the SPI pins to the correct mode and alt for PIO
        self._dc.init(mode=Pin.OUT)
        self._tx.init(mode=self._txMode, alt=self._txAlt)
        self._clk.init(mode=self._clkMode, alt=self._clkAlt)

        # Write to the display
        if self._cs:
            self._cs.off()
        if command is not None:
            self._dc.off()
            self._pio_write(command)
        if data is not None:
            self._dc.on()
            self._pio_write(data)
        if self._cs:
            self._cs.on()

        # Restore the SPI pins to their original mode and alt
        self._dc.init(mode=dcMode, alt=dcAlt)
        self._tx.init(mode=txMode, alt=txAlt)
        self._clk.init(mode=clkMode, alt=clkAlt)

    def _pio_write(self, data):
        """
        Writes data to the display using the PIO.

        Args:
            data (bytes, bytearray, or ndarray): Data to write to the display
        """
        # Configure the DMA transfer count and read address
        count = len(data) if isinstance(data, (bytes, bytearray)) else data.size
        self._dma.count = count
        self._dma.read = data
        
        # Start the state machine and DMA transfer, and wait for it to finish
        self._sm.active(1)
        self._dma.active(True)
        while self._dma.active():
            pass

        # Stop the state machine
        self._sm.active(0)

    @rp2.asm_pio(
            out_init = rp2.PIO.OUT_LOW,
            sideset_init = rp2.PIO.OUT_LOW,
            out_shiftdir = rp2.PIO.SHIFT_LEFT,
            autopull = True
        )
    def _pio_write_spi():
        """
        PIO program to write data to the display.
        """
        out(pins, 1).side(0)
        nop().side(1)
