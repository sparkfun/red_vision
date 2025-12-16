#-------------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# 
# Copyright (c) 2025 SparkFun Electronics
#-------------------------------------------------------------------------------
# red_vision/cameras/dvp_rp2_pio.py
#
# Red Vision DVP (Digital Video Port) camera interface using the RP2 PIO
# (Programmable Input/Output). Only available on Raspberry Pi RP2 processors.
# 
# This class is derived from:
# https://github.com/adafruit/Adafruit_ImageCapture/blob/main/src/arch/rp2040.cpp
# Released under the MIT license.
# Copyright (c) 2021 Adafruit Industries
#-------------------------------------------------------------------------------

import rp2
import array
from ulab import numpy as np
from machine import Pin, PWM
from uctypes import addressof
from ..utils import memory as rv_memory

class DVP_RP2_PIO():
    """
    Red Vision DVP (Digital Video Port) camera interface using the RP2 PIO
    (Programmable Input/Output). Only available on Raspberry Pi RP2 processors.
    """
    def __init__(
        self,
        sm_id,
        pin_d0,
        pin_vsync,
        pin_hsync,
        pin_pclk,
        pin_xclk = None,
    ):
        """
        Initializes the DVP interface with the specified parameters.

        Args:
            sm_id (int): PIO state machine ID
            pin_d0 (int): Data 0 pin number for DVP interface
            pin_vsync (int): Vertical sync pin number
            pin_hsync (int): Horizontal sync pin number
            pin_pclk (int): Pixel clock pin number
            pin_xclk (int, optional): External clock pin number
        """
        # Store state machine ID
        self._sm_id = sm_id

        # Store pin assignments
        self._pin_d0 = pin_d0
        self._pin_vsync = pin_vsync
        self._pin_hsync = pin_hsync
        self._pin_pclk = pin_pclk
        self._pin_xclk = pin_xclk

    def begin(
            self,
            buffer,
            xclk_freq,
            num_data_pins,
            byte_swap,
            continuous = False,
        ):
        """
        Begins the DVP interface with the specified parameters.

        Args:
            buffer (ndarray): Image buffer to write captured frames into
            xclk_freq (int): Frequency in Hz for the XCLK pin, if it is used
            num_data_pins (int): Number of data pins used by the camera (1 to 8)
            byte_swap (bool): Whether to swap bytes in each pixel
            continuous (bool, optional): Whether to continuously capture frames
                (default: False)
        """
        # Store buffer and its dimensions
        self._buffer = buffer
        self._height, self._width, self._bytes_per_pixel = buffer.shape

        # Initialize DVP pins as inputs
        self._num_data_pins = num_data_pins
        for i in range(num_data_pins):
            Pin(self._pin_d0+i, Pin.IN)
        Pin(self._pin_vsync, Pin.IN)
        Pin(self._pin_hsync, Pin.IN)
        Pin(self._pin_pclk, Pin.IN)

        # Set up XCLK pin if provided
        if self._pin_xclk is not None:
            self._xclk = PWM(Pin(self._pin_xclk))
            self._xclk.freq(xclk_freq)
            self._xclk.duty_u16(32768) # 50% duty cycle

        # If there's only 1 byte per pixel, we can safely transfer multiple
        # pixels at a time without worrying about byte alignment. So we use the
        # maximum of 4 pixels per transfer to improve DMA efficiency.
        if self._bytes_per_pixel == 1:
            self._bytes_per_transfer = 4
            # The PIO left shifts the pixel data in the FIFO buffer, so we need
            # to swap the bytes to get the correct order.
            byte_swap = True
        else:
            self._bytes_per_transfer = self._bytes_per_pixel

        # Store transfer parameters
        self._byte_swap = byte_swap

        # Whether to continuously capture frames
        self._continuous = continuous

        # Set up the PIO state machine
        self._setup_pio()

        # Set up the DMA controllers
        self._setup_dmas()

        # Set flag indicating the interface is not yet opened
        self._opened = False

    def buffer(self):
        """
        Returns the current frame buffer used by this driver.

        Returns:
            ndarray: Frame buffer
        """
        return self._buffer

    def open(self):
        """
        Captures a frame of data from the DVP interface.
        """
        # Check if already opened.
        if self._opened:
            return

        # Mark as opened.
        self._opened = True

        # If not in continuous mode, nothing else to do.
        if not self._continuous:
            return

        # We're in continuous mode, start capturing.
        self._start_capture()

    def release(self):
        # Check if already released.
        if not self._opened:
            return
        
        # Mark as not opened.
        self._opened = False

        # If not in continuous mode, nothing else to do.
        if not self._continuous:
            return

        # We're in continuous mode, stop capturing.
        self._stop_capture()

    def grab(self):
        """
        Captures a frame of data from the DVP interface.
        """
        # Check if opened.
        if not self._opened:
            # Not opened, cannot capture.
            return False
        
        # If we're in continuous mode, capturing is already happening.
        if self._continuous:
            return True

        # We're not in continuous mode, start a single capture.
        self._start_capture()

        # Stop the capture when it's done.
        self._stop_capture()

    def _setup_pio(self):
        """
        Sets up the PIO state machine for the DVP interface.
        """
        # Copy the PIO program
        program = self._pio_read_dvp

        # Mask in the GPIO pins
        program[0][0] |= self._pin_hsync & 0x1F
        program[0][1] |= self._pin_pclk & 0x1F
        program[0][3] |= self._pin_pclk & 0x1F

        # Mask in the number of data pins
        program[0][2] |= self._num_data_pins

        # Create PIO state machine to capture DVP data
        self._sm = rp2.StateMachine(
            self._sm_id,
            program,
            in_base = self._pin_d0,
            push_thresh = self._bytes_per_transfer * 8
        )

    # Here is the PIO program, which is configurable to mask in the GPIO pins
    # and the number of data pins. It must be configured before the state
    # machine is created
    @rp2.asm_pio(
            in_shiftdir = rp2.PIO.SHIFT_LEFT,
            autopush = True,
            fifo_join = rp2.PIO.JOIN_RX
        )
    def _pio_read_dvp():
        """
        PIO program to read DVP data from the GPIO pins.
        """
        wait(1, gpio, 0) # Mask in HSYNC pin
        wait(1, gpio, 0) # Mask in PCLK pin
        in_(pins, 32)    # Mask in number of pins
        wait(0, gpio, 0) # Mask in PCLK pin

    def _setup_dmas(self):
        """
        Sets up the DMA controllers for the DVP interface.
        """
        # This driver uses multiple DMA channels to transfer pixel data from the
        # camera to the image buffer. A detailed explanation and motive for this
        # DMA structure is better explained in the RP2 HSTX DVI driver, but an
        # abbreviated summary is provided here, along with some diagrams and
        # differences specific to the DVP interface.
        # 
        # One DMA channel (the "dispatcher") reads from a sequence of "control
        # blocks", and writes them to the control registers of a second DMA
        # channel (the "executer"). This pair of DMA channels continually
        # trigger and reconfigure each other, and are capable of transferring
        # data between any memory locations (including reconfiguring other
        # peripherals by writing their control registers) with zero CPU overhead
        # after initial configuration.
        # 
        # If the image buffer is in SRAM, the executer just transfers an entire
        # frame of data from the PIO RX FIFO to the image buffer with a single
        # control block. The second control block then makes the executer write
        # a third "nested" control block to the dispatcher, reconfiguring it to
        # start the next frame, resulting in continuous video capture.
        # 
        # +--------------------------+
        # |+------------+    +------+|      +-------+
        # || Row Buffer |<---|Pixels||<-----| Image |
        # |+------------+  ^ +------+|  DVP +-------+
        # || Ctrl Blocks|  | PIO FIFO|       Camera
        # |+------------+  |         |
        # |    SRAM |      |         |
        # |         |  +------------+|
        # |         |  |  Executer  ||
        # |         |  +------------+|
        # |         |        ^       |
        # |         |        |       |
        # |         |  +------------+|
        # |         +->| Dispatcher ||
        # |            +------------+|
        # +--------------------------+
        #            RP2350
        # 
        # If the image buffer is instead in PSRAM, transferring directly from
        # the PIO FIFO to PSRAM is not reliable, because some cameras (eg. the
        # OV5640) output each row of pixels in very short bursts that can exceed
        # the QSPI bus transfer speed. So instead, the executer DMA transfers
        # each row of pixel data to a small buffer in SRAM, then it triggers a
        # third DMA channel (the "streamer") with another "nested" control block
        # to transfer the row from SRAM to PSRAM as fast as the QSPI bus can
        # handle. Both transfers in and out of the row buffer can happen at the
        # same time, but the streamer starts earlier and stays ahead as long as
        # the camera's average data speed is not too fast.
        # 
        # The normal XIP memory mapped interface adds a lot of latency (see
        # section 4.4.3 of the RP2350 datasheet), so it could be beneficial to
        # use the QMI direct mode for the SRAM-to-PSRAM transfer (see section
        # 12.14.5 of the RP2350 datasheet). But the "bursty" cameras usually
        # have enough delay between each row that the normal memory mapped
        # interface is sufficient. The QMI direct mode also *dramatically*
        # complicates things, so this driver just uses the normal memory mapped
        # interface for simplicity.
        # 
        #              +--------------------------------------+
        # +-----+      |+------+    +------------+    +------+|      +-------+
        # |Image|<-----||Pixels|<---| Row Buffer |<---|Pixels||<-----| Image |
        # +-----+ QSPI |+------+  ^ +------------+  ^ +------+|  DVP +-------+
        #  PSRAM       |  XIP     | | Ctrl Blocks|  | PIO FIFO|       Camera
        #              |          | +------------+  |         |
        #              |          |     SRAM |      |         |
        #              | +------------+      |  +------------+|
        #              | |  Streamer  |<--------|  Executer  ||
        #              | +------------+      |  +------------+|
        #              |                     |        ^       |
        #              |                     |        |       |
        #              |                     |  +------------+|
        #              |                     +->| Dispatcher ||
        #              |                        +------------+|
        #              +--------------------------------------+
        #                               RP2350
        # 
        # When the image buffer is in PSRAM, the control block sequence is not
        # automatically restarted at the end of each frame. The QSPI bus can end
        # up being a real bottleneck if other things need to use it (eg.
        # processing other image buffers, display output, flash memory access,
        # etc.), so constantly spamming the QSPI bus with camera data can cause
        # other things to slow down, or even cause pixels from the camera to be
        # dropped if other transfers on the QSPI bus have higher priority. And
        # in most real applications, most frames from the camera are ignored
        # anyways, so it's better to just capture frames when needed.

        # Create the dispatcher and executer DMA channels.
        self._dma_dispatcher = rp2.DMA()
        self._dma_executer = rp2.DMA()

        # Check if the display buffer is in PSRAM.
        self._buffer_is_in_psram = rv_memory.is_in_external_ram(self._buffer)

        # If the buffer is in PSRAM, create the streamer DMA channel and row
        # buffer in SRAM.
        if self._buffer_is_in_psram:
            # Create the streamer DMA channel.
            self._dma_streamer = rp2.DMA()

            # Create the row buffer.
            self._bytes_per_row = self._width * self._bytes_per_pixel
            self._row_buffer = np.zeros((self._bytes_per_row), dtype=np.uint8)

            # Verify row buffer is in SRAM. If not, we'll still have the same
            # latency problem.
            if rv_memory.is_in_external_ram(self._row_buffer):
                raise MemoryError("not enough space in SRAM for row buffer")

        # Create DMA control register values.
        self._create_dma_ctrl_registers()

        # Create DMA control blocks.
        self._create_control_blocks()

        # Assemble the control blocks in order.
        self._assemble_control_blocks()

    def _create_dma_ctrl_registers(self):
        """
        Creates the DMA control register values.
        """
        # DMA DREQ (data request) signal selections for the RP2350 to pace
        # transfers by the peripheral data request signals. For some reason,
        # these are not defined in the `rp2.DMA` class.
        # 
        # According to section 12.6.4.1 of the RP2350 datasheet, the PIO RX DREQ
        # indices are determined by the PIO number (n) and state machine number
        # (m) as follows:
        # 
        # DREQ_PIOn_RXm = (n * 8) + 4 + m
        pio_num = self._sm_id // 4
        sm_num = self._sm_id % 4
        DREQ_PIO_RX = (pio_num * 8) + 4 + sm_num # Pace transfers with PIO RX FIFO data request
        DREQ_FORCE  = 63 # Transfer as fast as possible

        # Dispatcher control register. The "ring" parameters are used to have
        # the write address wrap around after 4 transfers (ring_sel = True means
        # wrap the write address, and ring_size = 4 specifies a 4-bit address
        # wrap, meaning 2**4 bits = 16 bits = 4 words), so the dispatcher
        # continuously re-writes the 4 control registers of the executer.
        self._dma_ctrl_cb_dispatcher = self._dma_dispatcher.pack_ctrl(
            # size      = 2,
            # inc_read  = True,
            # inc_write = True,
            ring_size   = 4,
            ring_sel    = True,
            # chain_to  = self._dma_dispatcher.channel,
            # treq_sel  = DREQ_FORCE,
            bswap       = False,
        )

        # Executer control register for getting pixel data from the PIO FIFO. It
        # transfers one pixel at a time (1, 2, or 4 bytes) and swaps bytes if
        # needed. Once done, it chains back to the dispatcher to get the next
        # control block.
        self._dma_ctrl_pio_repeat = self._dma_executer.pack_ctrl(
            size        = {1:0, 2:1, 4:2}[self._bytes_per_transfer],
            inc_read    = False,
            inc_write   = True,
            # ring_size = 0,
            # ring_sel  = False,
            chain_to    = self._dma_dispatcher.channel,
            treq_sel    = DREQ_PIO_RX,
            bswap       = self._byte_swap,
        )

        # Executer control register for sending nested control block to another
        # DMA channel without chaining back to the dispatcher.
        self._dma_ctrl_cb_executer_nested_single = self._dma_executer.pack_ctrl(
            # size      = 2,
            # inc_read  = True,
            # inc_write = True,
            # ring_size = 0,
            # ring_sel  = False,
            # chain_to  = self._dma_executer.channel,
            # treq_sel  = DREQ_FORCE,
            bswap       = False,
        )

        # If the display buffer is in PSRAM, we need additional DMA control
        # registers.
        if self._buffer_is_in_psram:
            # DMA control register for the executer to send a nested control
            # block with chaining back to the dispatcher, so another control
            # block can be sent immediately.
            self._dma_ctrl_cb_executer_nested_repeat = self._dma_executer.pack_ctrl(
                # size      = 2,
                # inc_read  = True,
                # inc_write = True,
                # ring_size = 0,
                # ring_sel  = False,
                chain_to    = self._dma_dispatcher.channel,
                # treq_sel  = DREQ_FORCE,
                bswap       = False,
            )

            # DMA control register for the streamer to transfer a row of pixel
            # data from the row buffer in SRAM to PSRAM.
            self._dma_ctrl_streamer = self._dma_streamer.pack_ctrl(
                # size      = 2,
                # inc_read  = True,
                # inc_write = False,
                # ring_size = 0,
                # ring_sel  = False,
                # chain_to  = self._dma_streamer.channel,
                # treq_sel  = DREQ_FORCE,
                bswap       = False,
            )

    def _create_control_blocks(self):
        """
        Creates the DMA control blocks.
        """
        # Determine how many control blocks are needed. The control block
        # sequence is created in `_assemble_control_blocks()`, but we need to
        # create the control block array early so the restart frame block can
        # reference it.
        num_cb = 0
        if not self._buffer_is_in_psram:
            num_cb += 1 # PIO read control block
            if self._continuous:
                num_cb += 1 # Restart frame control block
        else:
            num_cb += self._height # PIO read control blocks
            num_cb += self._height # Streamer control blocks

        # There are 4 words per control block.
        num_cb *= 4

        # Create control block array.
        self._control_blocks = array.array('I', [0] * num_cb)

        # Below are the individual control block definitions, to be written to
        # the alias 0 registers of each DMA channel (see section 12.6.3.1 of the
        # RP2350 datasheet). The registers are:
        # 
        # 1) READ_ADDR
        # 2) WRITE_ADDR
        # 3) TRANS_COUNT
        # 4) CTRL_TRIG
        #
        # When CTRL_TRIG is written, that DMA channel immediately starts.

        # Conveniently gets the RX FIFO address instead of TX
        pio_rx_fifo_addr = addressof(self._sm)

        # Control blocks are different depending on whether the buffer is in
        # SRAM or PSRAM.
        if not self._buffer_is_in_psram:
            # Control block for executer to read entire frame from PIO RX FIFO
            # to image buffer.
            self._cb_pio_repeat = array.array('I', [
                pio_rx_fifo_addr, # READ_ADDR
                addressof(self._buffer), # WRITE_ADDR
                self._width * self._height, # TRANS_COUNT
                self._dma_ctrl_pio_repeat, # CTRL_TRIG
            ])

            # Control blocks for restarting the dispatcher. `_cb_restart_frame`
            # must be the last control block in the sequence, which causes the
            # executer to write the nested `_cb_restart_frame_nested` control
            # block back to the dispatcher DMA registers, restarting it from the
            # beginning of the control block sequence.
            if self._continuous:
                self._cb_restart_frame_nested = array.array('I', [
                    addressof(self._control_blocks), # READ_ADDR
                    addressof(self._dma_executer.registers), # WRITE_ADDR
                    4, # TRANS_COUNT
                    self._dma_ctrl_cb_dispatcher, # CTRL_TRIG
                ])
                self._cb_restart_frame = array.array('I', [
                    addressof(self._cb_restart_frame_nested), # READ_ADDR
                    addressof(self._dma_dispatcher.registers), # WRITE_ADDR
                    len(self._cb_restart_frame_nested), # TRANS_COUNT
                    self._dma_ctrl_cb_executer_nested_single, # CTRL_TRIG
                ])
        else:
            # Control block for executer to read 1 row from PIO RX FIFO to image
            # buffer.
            self._cb_pio_repeat = array.array('I', [
                pio_rx_fifo_addr, # READ_ADDR
                addressof(self._row_buffer), # WRITE_ADDR
                self._bytes_per_row // self._bytes_per_transfer, # TRANS_COUNT
                self._dma_ctrl_pio_repeat, # CTRL_TRIG
            ])

            # Control blocks for the streamer DMA. `_cb_psram_repeat` and
            # `_cb_psram_single` cause the executer to write the nested
            # `_cb_psram_nested` control block to the streamer DMA registers,
            # triggering it to transfer the row buffer to PSRAM. Only the
            # `READ_ADDR_TRIG` register is used, since it's the only field that
            # needs to change. We do not want to change the write address (let
            # it keep incrementing to fill the whole image buffer), nor do we
            # need to change the transfer count or control register.
            self._cb_psram_nested = array.array('I', [
                addressof(self._row_buffer), # READ_ADDR_TRIG
            ])
            self._cb_psram_repeat = array.array('I', [
                addressof(self._cb_psram_nested), # READ_ADDR
                addressof(self._dma_streamer.registers[15:16]), # WRITE_ADDR
                len(self._cb_psram_nested), # TRANS_COUNT
                self._dma_ctrl_cb_executer_nested_repeat, # CTRL_TRIG
            ])
            self._cb_psram_single = array.array('I', [
                addressof(self._cb_psram_nested), # READ_ADDR
                addressof(self._dma_streamer.registers[15:16]), # WRITE_ADDR
                len(self._cb_psram_nested), # TRANS_COUNT
                self._dma_ctrl_cb_executer_nested_single, # CTRL_TRIG
            ])

    def _assemble_control_blocks(self):
        """
        Assembles the complete control block sequence to send the image buffer
        over DVI, which includes sending all timing signals and pixel data to
        the HSTX, starting the XIP stream and PSRAM DMA if needed, and
        restarting the control block sequence for the next frame.
        """
        # Reset the control block index.
        self._cb_index = 0

        # Control blocks are different depending on whether the buffer is in
        # SRAM or PSRAM.
        if not self._buffer_is_in_psram:
            # Add control block for executer to read entire frame from PIO RX
            # FIFO to image buffer.
            self._add_control_block(self._cb_pio_repeat)

            # If continuous mode is requested, add control block to restart the
            # control block sequence reconfiguring the dispatcher DMA.
            if self._continuous:
                self._add_control_block(self._cb_restart_frame)
        else:
            # Loop through each row of the image.
            for row in range(self._height):
                # Add control block for executer to read 1 row from PIO RX FIFO
                # to image buffer.
                self._add_control_block(self._cb_pio_repeat)

                # Add control block for streamer to send row from SRAM to PSRAM.
                self._add_control_block(self._cb_psram_repeat)

            # Overwrite the last control block to be a single transfer without
            # chaining, so the control block sequence properly ends.
            self._cb_index -= 4
            self._add_control_block(self._cb_psram_single)

    def _add_control_block(self, block):
        """
        Helper function to add a control block to the control block array.

        Args:
            block (array): Control block to add
        """
        # Add the control block to the array. Each control block is all 4 DMA
        # alias 0 registers in order.
        self._control_blocks[self._cb_index + 0] = block[0] # READ_ADDR
        self._control_blocks[self._cb_index + 1] = block[1] # WRITE_ADDR
        self._control_blocks[self._cb_index + 2] = block[2] # TRANS_COUNT
        self._control_blocks[self._cb_index + 3] = block[3] # CTRL_TRIG

        # Increment the control block index for the next control block.
        self._cb_index += 4

    def _start_capture(self):
        """
        Starts capturing frames from the DVP interface. Waits for falling edge
        on VSYNC to ensure the current frame is complete.
        """
        # If the image buffer is in PSRAM, the streamer DMA channel needs to
        # be reconfigured for each frame to reset the write address.
        if self._buffer_is_in_psram:
            self._dma_streamer.config(
                read = addressof(self._row_buffer), # READ_ADDR
                write = addressof(self._buffer), # WRITE_ADDR
                count = self._bytes_per_row // 4, # TRANS_COUNT
                ctrl = self._dma_ctrl_streamer, # CTRL
                trigger = False,
            )
        
        # Configure the dispatcher DMA channel to start the control block
        # sequence, but don't trigger it yet.
        self._dma_dispatcher.config(
            read = addressof(self._control_blocks), # READ_ADDR
            write = addressof(self._dma_executer.registers), # WRITE_ADDR
            count = 4, # TRANS_COUNT
            ctrl = self._dma_ctrl_cb_dispatcher, # CTRL
            trigger = False,
        )

        # Wait for a falling edge on VSYNC, indicating the end of the frame.
        while Pin(self._pin_vsync, Pin.IN).value() == False:
            pass
        while Pin(self._pin_vsync, Pin.IN).value() == True:
            pass
        
        # Activate the state machine and reset it.
        self._sm.active(True)
        self._sm.restart()
        while self._sm.rx_fifo() > 0:
            self._sm.get()
        
        # Start the dispatcher DMA channel.
        self._dma_dispatcher.active(True)

    def _stop_capture(self):
        """
        Stops capturing frames from the DVP interface. Waits for falling edge on
        VSYNC to ensure the current frame is complete.
        """
        # Wait for a falling edge on VSYNC, indicating the end of the frame.
        while Pin(self._pin_vsync, Pin.IN).value() == False:
            pass
        while Pin(self._pin_vsync, Pin.IN).value() == True:
            pass

        # Deactivate the state machine.
        self._sm.active(False)
