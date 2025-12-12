#-------------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# 
# Copyright (c) 2025 SparkFun Electronics
#-------------------------------------------------------------------------------
# red_vision/displays/dvi_rp2_hstx.py
# 
# Red Vision DVI/HDMI display driver using the RP2350 HSTX interface. Only
# available on Raspberry Pi RP2 processors.
# 
# This class is partially derived from:
# https://github.com/adafruit/circuitpython/blob/main/ports/raspberrypi/common-hal/picodvi/Framebuffer_RP2350.c
# Released under the MIT license.
# Copyright (c) 2023 Scott Shawcroft for Adafruit Industries
#-------------------------------------------------------------------------------

# Imports
import rp2
import machine
import array
from uctypes import addressof
from ulab import numpy as np
from ..utils import colors as rv_colors
from ..utils import memory as rv_memory

class DVI_RP2_HSTX():
    """
    Red Vision DVI/HDMI display driver using the RP2350 HSTX interface. Only
    available on Raspberry Pi RP2 processors.

    Because the HSTX is capable of double data rate (DDR) signaling, it is the
    fastest way to output DVI from the RP2350.
    """
    # Below is a reference video timing diagram. Source:
    # https://projectf.io/posts/video-timings-vga-720p-1080p/#video-signals-in-brief
    # 
    # +-------------------------------+---+
    # |            Porches            |   |<- Vertical back porch
    # |   +-----------------------+   |   |
    # |   |                       |   |   |
    # |   |                       |   |   |
    # |   |                       |   |   |
    # |   |     Active Pixels     |   |   |<- Vertical active lines
    # |   |                       |   |   |
    # |   |                       |   |   |
    # |   |                       |   |   |
    # |   +-----------------------+   |   |
    # |                               |   |<- Vertical front porch
    # +-------------------------------+   |
    # |             Syncs                 |<- Vertical sync
    # +-----------------------------------+
    #   ^             ^             ^   ^  
    #   |             |             |   |  
    #   |             |             |   +---- Horizontal sync
    #   |             |             +-------- Horizontal front porch
    #   |             +---------------------- Horizontal active pixels
    #   +------------------------------------ Horizontal back porch
    # 
    # To simplify things, we can wrap the front porches and syncs around to the
    # top and left sides, putting the active pixels in the bottom right corner:
    # 
    # +---+---+----------------------------
    # |   |   |                           |<- Vertical front porch
    # +---+   +----------------------------
    # |                     Syncs         |<- Vertical sync
    # +---+   +----------------------------
    # |   |   |            Porches        |<- Vertical back porch
    # |   |   |   +-----------------------+
    # |   |   |   |                       |
    # |   |   |   |                       |
    # |   |   |   |                       |
    # |   |   |   |     Active Pixels     |<- Vertical active lines
    # |   |   |   |                       |
    # |   |   |   |                       |
    # |   |   |   |                       |
    # +---+---+---+-----------------------+
    #   ^   ^   ^             ^
    #   |   |   |             |
    #   |   |   |             +-------------- Horizontal active pixels
    #   |   |   +---------------------------- Horizontal back porch
    #   |   +-------------------------------- Horizontal sync
    #   +------------------------------------ Horizontal front porch
    #
    # This helps simplify the driver by just sending each active line as a chunk
    # of horizontal timing signals followed by a row of pixel data. Each corner
    # is equally valid, because the signal is continuous, so the display will
    # have no idea how we've arranged it internally. It's especially convenient
    # to have the horizontal timing signals left of the pixel data, because the
    # HSTX needs a command to be sent before the pixel data for each line.

    # Porch and sync timings for different resolutions can be found here:
    # https://projectf.io/posts/video-timings-vga-720p-1080p/
    # This driver currently only supports 640x480.
    _H_FRONT_PORCH   = 16
    _H_SYNC_WIDTH    = 96
    _H_BACK_PORCH    = 48
    _H_ACTIVE_PIXELS = 640

    _V_FRONT_PORCH  = 10
    _V_SYNC_WIDTH   = 2
    _V_BACK_PORCH   = 33
    _V_ACTIVE_LINES = 480

    _H_TOTAL_PIXELS = _H_FRONT_PORCH + _H_SYNC_WIDTH + _H_BACK_PORCH + _H_ACTIVE_PIXELS
    _V_BLANK_LINES  = _V_FRONT_PORCH + _V_SYNC_WIDTH + _V_BACK_PORCH
    _V_TOTAL_LINES  = _V_FRONT_PORCH + _V_SYNC_WIDTH + _V_BACK_PORCH + _V_ACTIVE_LINES

    def __init__(
            self,
            pin_clk_p  = 14,
            pin_clk_n  = 15,
            pin_d0_p   = 18,
            pin_d0_n   = 19,
            pin_d1_p   = 16,
            pin_d1_n   = 17,
            pin_d2_p   = 12,
            pin_d2_n   = 13,
        ):
        """
        Initializes the DVI HSTX display driver.

        Args:
            width (int): Display width in pixels
            height (int): Display height in pixels
            color_mode (int, optional): Color mode
              - COLOR_BGR233: 8-bit BGR233
              - COLOR_GRAY8: 8-bit grayscale
              - COLOR_BGR565: 16-bit BGR565 (default)
              - COLOR_BGRA8888: 32-bit BGRA8888
            pin_clk_p (int, optional): TMDS clock lane positive pin (default: 14)
            pin_clk_n (int, optional): TMDS clock lane negative pin (default: 15)
            pin_d0_p (int, optional): TMDS data 0 lane positive pin (default: 18)
            pin_d0_n (int, optional): TMDS data 0 lane negative pin (default: 19)
            pin_d1_p (int, optional): TMDS data 1 lane positive pin (default: 16)
            pin_d1_n (int, optional): TMDS data 1 lane negative pin (default: 17)
            pin_d2_p (int, optional): TMDS data 2 lane positive pin (default: 12)
            pin_d2_n (int, optional): TMDS data 2 lane negative pin (default: 13)
            buffer (ndarray, optional): Pre-allocated frame buffer.
        """
        # Set pin numbers.
        self._pin_clk_p = pin_clk_p
        self._pin_clk_n = pin_clk_n
        self._pin_d0_p = pin_d0_p
        self._pin_d0_n = pin_d0_n
        self._pin_d1_p = pin_d1_p
        self._pin_d1_n = pin_d1_n
        self._pin_d2_p = pin_d2_p
        self._pin_d2_n = pin_d2_n

    def begin(self, buffer, color_mode):
        """
        Begins DVI output.
        """
        # Store buffer and color mode.
        self._buffer = buffer
        self._color_mode = color_mode
        self._height, self._width, self._bytes_per_pixel = self._buffer.shape

        # Set resolution and scaling factors.
        self._width_scale = self._H_ACTIVE_PIXELS // self._width
        self._height_scale = self._V_ACTIVE_LINES // self._height

        # Configure HSTX peripheral.
        self._configure_hstx()

        # Configure DMA channels.
        self._configure_dmas()

        # Start DVI output.
        self._start()

    def resolution_default(self):
        """
        Returns the default resolution for the display.
        """
        return (self._V_ACTIVE_LINES // 2, self._H_ACTIVE_PIXELS // 2)

    def resolution_is_supported(self, height, width):
        """
        Checks if the given resolution is supported by the display.

        Args:
            height (int): Height in pixels
            width (int): Width in pixels
        Returns:
            bool: True if the resolution is supported, otherwise False
        """
        # Check if width and height are factors of active pixels/lines.
        width_supported = (self._H_ACTIVE_PIXELS % width == 0)
        height_supported = (self._V_ACTIVE_LINES % height == 0)

        # Check if either is not a factor.
        if not width_supported or not height_supported:
            return False
        
        # Both are factors, but width can only be upscaled to a maximum of 32x.
        return self._H_ACTIVE_PIXELS / width <= 32

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

    def _configure_hstx(self):
        """
        Configures the HSTX peripheral for DVI output using the TMDS encoder.
        """
        # Create HSTX object.
        self._hstx = rp2.HSTX()

        # Configure the HSTX command expander shift register. This driver uses
        # the HSTX command expander to send the pixel data to the TMDS encoder.
        # 
        # It's possible to have the encoder output multiple pixels per word in
        # the HSTX FIFO, specified by the `enc_n_shifts` field. This is utilized
        # for the width scaling feature, where the same pixel is sent multiple
        # times to "upscale" the row of pixels to the native monitor resolution.
        # It's also possible to pack multiple pixels into a single word in the
        # FIFO, then utilize `enc_shift` to shift the bits to align susequent
        # pixel bits for the encoder, but this implementation only packs one
        # pixel per word for simplicity.
        # 
        # For the timing signals, the "raw" commands are used. Each word in the
        # FIFO is one complete timing symbol, so `raw_n_shifts` and `raw_shift`
        # are set to 1 and 0, respectively.
        expand_shift = self._hstx.pack_expand_shift(
            enc_n_shifts = self._width_scale % 32,
            enc_shift = 0,
            raw_n_shifts = 1,
            raw_shift = 0
        )
        self._hstx.expand_shift(expand_shift)

        # Configure the HSTX TMDS encoder based on the selected color mode.
        # 
        # There are 3 TMDS data lanes for DVI video. Lane 0 carries the blue
        # channel, lane 1 carries green, and lane 2 carries red.
        # 
        # This driver puts a full pixel's worth of data in the HSTX's 32-bit
        # FIFO buffer, which are read one pixel at a time by the TMDS encoder.
        # Each lane requires the bits for that channel to start at bit 7 (8th
        # bit position), so each lane needs to shift the register to get the MSB
        # aligned using the `ln_rot` field (right rotate, wraps around). Up to 8
        # bits can be used per channel, specified by the `ln_nbits` field
        # (values of 0-7 correspond to 1-8 bits). If fewer than 8 bits are used
        # for a channel, the output is padded with zeros, limiting the maximum
        # value (and therefore, pixel brightness) for that channel.
        # 
        # With BGR color modes, B is the least significant bits, and R is the
        # most significant bits. This means the bits are in RGB order, which is
        # opposite of what one might expect.
        if self._color_mode == rv_colors.COLOR_MODE_BGR233:
            # BGR233 (00000000 00000000 00000000 RRRGGGBB)
            expand_tmds = self._hstx.pack_expand_tmds(
                l2_nbits =  2, # 3 bits (red)
                l2_rot   =  0, # Shift right  0 bits to align MSB
                l1_nbits =  2, # 3 bits (green)
                l1_rot   = 29, # Shift right 29 bits to align MSB (left 3 bits)
                l0_nbits =  1, # 2 bits (blue)
                l0_rot   = 26, # Shift right 26 bits to align MSB (left 6 bits)
            )
        elif self._color_mode == rv_colors.COLOR_MODE_GRAY8:
            # GRAY8 (00000000 00000000 00000000 GGGGGGGG)
            expand_tmds = self._hstx.pack_expand_tmds(
                l2_nbits =  7, # 8 bits (red)
                l2_rot   =  0, # Shift right  0 bits to align MSB
                l1_nbits =  7, # 8 bits (green)
                l1_rot   =  0, # Shift right  0 bits to align MSB
                l0_nbits =  7, # 8 bits (blue)
                l0_rot   =  0, # Shift right  0 bits to align MSB
            )
        elif self._color_mode == rv_colors.COLOR_MODE_BGR565:
            # BGR565 (00000000 00000000 RRRRRGGG GGGBBBBB)
            expand_tmds = self._hstx.pack_expand_tmds(
                l2_nbits =  4, # 5 bits (red)
                l2_rot   =  8, # Shift right  8 bits to align MSB
                l1_nbits =  5, # 6 bits (green)
                l1_rot   =  3, # Shift right  3 bits to align MSB
                l0_nbits =  4, # 5 bits (blue)
                l0_rot   = 29, # Shift right 29 bits to align MSB (left 3 bits)
            )
        elif self._color_mode == rv_colors.COLOR_MODE_BGRA8888:
            # BGRA8888 (AAAAAAAA RRRRRRRR GGGGGGGG BBBBBBBB) alpha is ignored
            expand_tmds = self._hstx.pack_expand_tmds(
                l2_nbits =  7, # 8 bits (red)
                l2_rot   = 16, # Shift right 16 bits to align MSB
                l1_nbits =  7, # 8 bits (green)
                l1_rot   =  8, # Shift right  8 bits to align MSB
                l0_nbits =  7, # 8 bits (blue)
                l0_rot   =  0, # Shift right  0 bits to align MSB
            )
        self._hstx.expand_tmds(expand_tmds)

        # Set which GPIO pins output which data bits.
        # 
        # After the TMDS encoder (or just the raw data for timing signals), the
        # data is sent to the Bit Crossbar, which determines which GPIO pin
        # output which bits of data. In this case, there will be 30 bits of data
        # with 10 bits designated for each TMDS lane, and the top 2 bits unused:
        # 
        # (xx 2222222222 1111111111 0000000000)
        # 
        # The HSTX is capable of DDR (double data rate), meaning each GPIO pin
        # can output data on both the rising and falling edges of the system
        # clock. We utilize this for maximum transfer speed, where `sel_p` and
        # `sel_n` select which bits in the output shift register are output on
        # the rising and falling edges of each system clock cycle per GPIO pin.
        # The output shift register will be configured to shift by 2 bits every
        # full cycle for 5 cycles, so each pin needs have `sel_p` and `sel_n`
        # set to `10*n` and `10*n+1` for lane n.
        # 
        # The TMDS clock lane just outputs a continuous clock signal, so those
        # GPIO pins just follow the HSTX clock generator, which will be
        # configured below
        # 
        # Each lane is a differential pair, so the `_n` pin of each pair is the
        # same as the `_p` pin but inverted.
        self._hstx.bit(self._pin_clk_p, self._hstx.pack_bit(clk=1,              inv=0))
        self._hstx.bit(self._pin_clk_n, self._hstx.pack_bit(clk=1,              inv=1))
        self._hstx.bit(self._pin_d0_p,  self._hstx.pack_bit(sel_p= 0, sel_n= 1, inv=0))
        self._hstx.bit(self._pin_d0_n,  self._hstx.pack_bit(sel_p= 0, sel_n= 1, inv=1))
        self._hstx.bit(self._pin_d1_p,  self._hstx.pack_bit(sel_p=10, sel_n=11, inv=0))
        self._hstx.bit(self._pin_d1_n,  self._hstx.pack_bit(sel_p=10, sel_n=11, inv=1))
        self._hstx.bit(self._pin_d2_p,  self._hstx.pack_bit(sel_p=20, sel_n=21, inv=0))
        self._hstx.bit(self._pin_d2_n,  self._hstx.pack_bit(sel_p=20, sel_n=21, inv=1))

        # Set all HSTX pins (GPIO 12-19) to ALT function for HSTX output.
        for i in range(12, 20):
            machine.Pin(i, mode=machine.Pin.ALT, alt=machine.Pin.ALT_HSTX)

        # Setup the HSTX control register.
        # 
        # Because we're using DDR (double data rate), the HSTX outputs 2 data
        # bits per system clock cycle. DVI requires the clock lane to cycle once
        # per 10 data bits, meaning every 5 system clock cycles, so `clk_div` is
        # set to 5.
        # 
        # The bit crossbar configured above expects the output shift register to
        # shift by 2 bits every system clock cycle for 5 cycles, so `shift` and
        # `n_shifts` are set to 2 and 5, respectively.
        # 
        # The command expander is enabled to enable the TMDS encoder by setting
        # `expand_enable` to 1.
        # 
        # Finally, the HSTX peripheral is enabled by setting `enable` to 1.
        csr = self._hstx.pack_csr(
            clk_div = 5,
            # clk_phase = 0,
            n_shifts = 5,
            shift = 2,
            # coupled_select = 0,
            # coupled_mode = 0,
            expand_enable = 1,
            enable = 1
        )
        self._hstx.csr(csr)

    def _configure_dmas(self):
        """
        Configures the DMA channels to transfer the required data to the HSTX
        peripheral for DVI output.
        """
        # This gets complicated, brace yourself!
        # 
        # The HSTX peripheral has a small FIFO buffer that needs to be kept
        # filled with data. Doing this with the CPU would tie it up forever,
        # because DVI signals require a continuous stream of data. The CPU would
        # likely be too slow anyways, so we instead use a DMA channel to fill
        # the FIFO buffer.
        # 
        # When a DMA channel is configured for a transfer, it can only transfer
        # from one contiguous block of memory to another contiguous block of
        # memory. The memory blocks can be a single address or even wrap around,
        # but the channel can't jump around to different memory locations on its
        # own. The DVI video signal has to alternate between timing signals and
        # pixel data, so sending that interleaved data with a single DMA channel
        # configuration would require a large buffer with everything mixed
        # together; that would be very wasteful, and updating the image becomes
        # more complicated (in other words, slow). Instead, we keep the timing
        # signals and pixel data in separate memory locations, and reconfigure
        # the DMA channel on-the-fly to alternate between them.
        # 
        # An interrupt could be used to reconfigure the DMA channel when it
        # completes each transfer, but MicroPython interrupts take too long (a
        # few microseconds). The HSTX FIFO buffer ends up running out of data
        # before the interrupt can reconfigure the channel, resulting in pauses
        # in the video signal. DVI signals require *very* precise timing, so
        # pauses are not acceptable. Even if interrupts were fast enough, it
        # would consume a *lot* of CPU time.
        # 
        # The solution is to use a second DMA channel that reconfigures the
        # first channel when each transfer completes. DMA channels are capable
        # of 1 transfer per clock cycle, so that's plenty fast enough to rewrite
        # the first channel's 4 control registers before the HSTX FIFO runs out.
        # The second DMA reads from a sequence of "control blocks" in memory,
        # which are just sets of control register values, and writes them to the
        # first channel's control registers. This is explained in more detail in
        # section 12.6 of the RP2350 datasheet; see section 12.6.9.2 for a much
        # simpler example than this implementation.
        # 
        # You can think of the second DMA channel as "dispatching" control
        # blocks to the first DMA channel, which "executes" them. So this driver
        # calls them "dispatcher" and "executer" DMA channels. The dispatcher
        # triggers the executer when the 4th control register is written (see
        # `CTRL_TRIG` registers in section 12.6.3.1 of the RP2350 datasheet).
        # The executer then triggers the dispatcher when it completes its
        # transfer by using the "chain to" parameter in its control register,
        # causing the channels to continuously trigger each other.
        # 
        # +---------------------------+
        # |+------------+    +-------+|      +-------+
        # ||   Buffer   |-+->| Data  ||----->| Image |
        # |+------------+ |  +-------+| DVI  +-------+
        # || Line Porch |-+  HSTX FIFO|       Display
        # |+------------+ |           |
        # || Line Sync  |-+           |
        # |+------------+ |           |
        # || Line Active|-+           |
        # |+------------+ ^           |
        # || Ctrl Blocks| |           |
        # |+------------+ |           |
        # |    SRAM |     |           |
        # |         |  +------------+ |
        # |         |  |  Executer  | |
        # |         |  +------------+ |
        # |         |        ^        |
        # |         |        |        |
        # |         |  +------------+ |
        # |         +->| Dispatcher | |
        # |            +------------+ |
        # +---------------------------+
        #            RP2350
        # 
        # The control blocks can change the executer's read and write addresses,
        # transfer count, and control register settings on-the-fly. This allows
        # the pair of DMA channels to effectively move data between any memory
        # locations (including reconfiguring other peripherals by writing their
        # control registers), with various transfer sizes and settings, giving a
        # lot of flexibility. For the most part, the read address and transfer
        # count of the executer just changes between the timing signal data and
        # pixel data, always sending to the HSTX FIFO.
        # 
        # The 2 DMA channels continue triggering each other until the end of the
        # control block sequence, at which point the dispatcher needs to be
        # reconfigured to start the next frame. Again, MicroPython interrupts
        # are too slow for this. Instead, the dispatcher can send a control
        # block to the executer that makes it write a "nested" control block
        # back to the dispatcher, reconfiguring it to start the next frame. This
        # means a continuous video signal can be generated with zero CPU usage
        # after the initial setup.
        # 
        # The main downside to using control blocks is that DMA channels have no
        # logic processing capabilities, so the logic needs to be pre-determined
        # by the order of the control blocks in memory. To send a full 640x480
        # frame of data, ~5k control blocks are needed, consuming ~20kB of RAM.
        # So the tradeoff is higher memory usage, but the benefit is zero CPU
        # usage after initial setup, and the HSTX FIFO is always kept full,
        # resulting in a stable video signal. It's also less memory usage than
        # creating a giant mixed buffer of timing signals and pixel data.
        # 
        # This works great if the display buffer is in SRAM, but if it's in
        # PSRAM (it most likely will be, image buffers are large!), there is
        # another problem. Section 4.4.3 of the RP2350 datasheet goes into more
        # detail, but when using the normal memory mapped XIP interface to
        # access data in PSRAM, a lot of latency can be added to each transfer.
        # This can cause the executer DMA channel to take too long to retrive
        # data from PSRAM, resulting in the HSTX FIFO running out of data,
        # meaning pauses in the video signal and an unhappy monitor.
        # 
        # To solve this, we use the XIP streaming interface, which is designed
        # for bulk data transfers from flash or PSRAM (both are on the same QSPI
        # bus) while still allowing code execution from flash (see section 4.4.3
        # of the RP2350 datasheet for more details). The data is put into the
        # XIP stream FIFO, from which the data can be acquired. It can't be
        # transferred directly from the XIP FIFO to the HSTX FIFO, because there
        # will still be some latency, especially if other activity is happening
        # on the QSPI bus (eg. the CPU fetching code from flash).
        # 
        # So, we use a third DMA channel! This driver calls it the "streamer"
        # DMA channel, because it transfers one row of pixel data at a time from
        # the XIP stream FIFO to a small buffer in SRAM. When a row of pixel
        # data is needed, the executer DMA channel triggers the streamer to fill
        # the row buffer with another "nested" control block, then the executer
        # transfers the row buffer to the HSTX FIFO. Both transfers end up
        # happening at the same time, but the streamer starts slightly earlier
        # and stays ahead as long as the PSRAM transfer speed is fast enough.
        # 
        #              +---------------------------------------+
        # +-----+      |+------+    +------------+    +-------+|      +-------+
        # |Image|----->||Pixels|--->| Row Buffer |-+->| Data  ||----->| Image |
        # +-----+ QSPI |+------+ ^  +------------+ |  +-------+| DVI  +-------+
        #  PSRAM       |XIP FIFO |  | Line Porch |-+  HSTX FIFO|       Display
        #              |         |  +------------+ |           |
        #              |         |  | Line Sync  |-+           |
        #              |         |  +------------+ |           |
        #              |         |  | Line Active|-+           |
        #              |         |  +------------+ ^           |
        #              |         |  | Ctrl Blocks| |           |
        #              |         |  +------------+ |           |
        #              |         |      SRAM |     |           |
        #              | +------------+      |  +------------+ |
        #              | |  Streamer  |<--------|  Executer  | |
        #              | +------------+      |  +------------+ |
        #              |                     |        ^        |
        #              |                     |        |        |
        #              |                     |  +------------+ |
        #              |                     +->| Dispatcher | |
        #              |                        +------------+ |
        #              +---------------------------------------+
        #                               RP2350

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

            # Verify that PSRAM transfer speed is sufficient for specified
            # resolution and color mode. The RP2350 system clock is typically
            # 150 MHz, and the HSTX transmits 1 pixel every 5 clock cycles, so
            # 30 megapixels per second. The QSPI bus clock is typically half the
            # system clock (150 MHz / 2 = 75 MHz), and 1 byte per 2 clock cycles
            # (quad-SPI), so 37.5 Mbytes/second. So for native resolution (no
            # scaling), only color modes with 1 byte per pixel are possible (eg.
            # BGR233 or GRAY8). Larger color modes (2 or 4 bytes per pixel) can
            # only be used with scaling.
            hstx_pixels_per_second = machine.freq() / 5
            psram_bytes_per_second = rv_memory.external_ram_max_bytes_per_second()
            psram_pixels_per_second = psram_bytes_per_second * self._width_scale / self._bytes_per_pixel
            if psram_pixels_per_second < hstx_pixels_per_second:
                raise ValueError("PSRAM transfer speed too low for specified resolution and color mode")

            # Create the row buffer.
            self._bytes_per_row = self._width * self._bytes_per_pixel
            self._row_buffer = np.zeros((self._bytes_per_row), dtype=np.uint8)

            # Verify row buffer is in SRAM. If not, we'll still have the same
            # latency problem.
            if rv_memory.is_in_external_ram(self._row_buffer):
                raise MemoryError("not enough space in SRAM for row buffer")

            # We'll use a DMA to trigger the XIP stream. However the RP2350's
            # default security settings do not allow DMA access to the XIP_CTRL
            # registers; attempting to write to them causing the DMA to stop
            # with a bus error that is not immediately obvious... So, we need to
            # unlock DMA access to the XIP_CTRL registers.
            ACCESSCTRL_BASE = 0x40060000
            XIP_CTRL = ACCESSCTRL_BASE + 0xE0

            # In the entire RP2350 datasheet, there is only one mention in
            # section 10.6 about password bits required to write the ACCESSCTRL
            # registers; the top 16 bits must be `0xACCE`, otherwise a bus
            # fault occurs, causing the processor to freeze... So we need to
            # add those bits.
            ACCESSCTRL_PASSWORD_BITS = 0xACCE0000

            # The default register value is 0b10111000, where bit 6 is the DMA
            # bit. It defaults to 0, so we just need to set it to 1, to allow
            # DMA access to the XIP_CTRL registers.
            machine.mem32[XIP_CTRL] = ACCESSCTRL_PASSWORD_BITS | 0b11111000

        # Create DMA control register values.
        self._create_dma_ctrl_registers()

        # Create DMA control blocks.
        self._create_control_blocks()

        # Assemble the control blocks in order.
        self._assemble_control_blocks()

        # Configure the dispatcher DMA channel with the restart frame control
        # block contents. Don't start it yet, `_start()` will do that.
        self._dma_dispatcher.config(
            read = self._cb_restart_frame_nested[0], # READ_ADDR
            write = self._cb_restart_frame_nested[1], # WRITE_ADDR
            count = self._cb_restart_frame_nested[2], # TRANS_COUNT
            ctrl = self._cb_restart_frame_nested[3], # CTRL
            trigger = False,
        )

    def _create_dma_ctrl_registers(self):
        """
        Creates the DMA control register values.
        """
        # DMA DREQ (data request) signal selections for the RP2350. For some
        # reason, these are not defined in the `rp2.DMA` class.
        DREQ_XIP_STREAM = 49 # Pace transfers with XIP stream FIFO data request
        DREQ_HSTX       = 52 # Pace transfers with HSTX FIFO data request
        DREQ_FORCE      = 63 # Transfer as fast as possible

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

        # Executer control register for sending HSTX timing commands to the HSTX
        # FIFO. Once done, it chains back to the dispatcher to get the next
        # control block.
        self._dma_ctrl_hstx_commands = self._dma_executer.pack_ctrl(
            # size      = 2,
            # inc_read  = True,
            inc_write   = False,
            # ring_size = 0,
            # ring_sel  = False,
            chain_to    = self._dma_dispatcher.channel,
            treq_sel    = DREQ_HSTX,
            bswap       = False,
        )

        # Executer control register for sending HSTX pixel data to the HSTX
        # FIFO. Once done, it chains back to the dispatcher to get the next
        # control block.
        self._dma_ctrl_hstx_pixels = self._dma_executer.pack_ctrl(
            size        = {1:0, 2:1, 4:2}[self._bytes_per_pixel],
            # inc_read  = True,
            inc_write   = False,
            # ring_size = 0,
            # ring_sel  = False,
            chain_to    = self._dma_dispatcher.channel,
            treq_sel    = DREQ_HSTX,
            bswap       = False,
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
            # data from the XIP stream FIFO to the row buffer in SRAM.
            self._dma_ctrl_streamer = self._dma_streamer.pack_ctrl(
                # size      = 2,
                inc_read    = False,
                # inc_write = True,
                # ring_size = 0,
                # ring_sel  = False,
                # chain_to  = self._dma_streamer.channel,
                treq_sel    = DREQ_XIP_STREAM,
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
        num_cb += self._V_FRONT_PORCH # Front porch line control blocks
        num_cb += self._V_SYNC_WIDTH # VSYNC line control blocks
        num_cb += self._V_BACK_PORCH # Back porch line control blocks
        num_cb += self._V_ACTIVE_LINES # Active line control blocks
        num_cb += self._V_ACTIVE_LINES # Pixel line control blocks
        num_cb += 1 # Restart frame control block

        # Extra control blocks are needed if the buffer is in PSRAM.
        if self._buffer_is_in_psram:
            num_cb += 1 # Start PSRAM DMA control block
            num_cb += 1 # Stop PSRAM DMA control block
            num_cb += 1 # Start XIP stream control block
            num_cb += self._V_ACTIVE_LINES // self._height_scale # Start PSRAM DMA control blocks

        # There are 4 words per control block.
        num_cb *= 4

        # Create control block array.
        self._control_blocks = array.array('I', [0] * num_cb)

        # The control block array must be in SRAM, otherwise we run into the
        # same latency problem with DMA transfers from PSRAM.
        if rv_memory.is_in_external_ram(self._control_blocks):
            raise MemoryError("not enough space in SRAM for control block array")

        # Create the HSTX command sequences so the control blocks can reference
        # them.
        self._create_hstx_commands()

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

        # Control blocks for executer to send HSTX command sequences to the HSTX
        # FIFO. Includes command sequences for the timing signals and the active
        # pixel data. For the pixel control block, the read address is a dummy
        # value that needs to be changed later, depending on whether the buffer
        # is in SRAM or PSRAM (see `_assemble_control_blocks()`).
        HSTX_FIFO_BASE = 0x50600000
        HSTX_FIFO = HSTX_FIFO_BASE + 0x4
        self._cb_line_porch = array.array('I', [
            addressof(self._hstx_line_porch), # READ_ADDR
            HSTX_FIFO, # WRITE_ADDR
            len(self._hstx_line_porch), # TRANS_COUNT
            self._dma_ctrl_hstx_commands, # CTRL_TRIG
        ])
        self._cb_line_vsync = array.array('I', [
            addressof(self._hstx_line_vsync), # READ_ADDR
            HSTX_FIFO, # WRITE_ADDR
            len(self._hstx_line_vsync), # TRANS_COUNT
            self._dma_ctrl_hstx_commands, # CTRL_TRIG
        ])
        self._cb_line_active = array.array('I', [
            addressof(self._hstx_line_active), # READ_ADDR
            HSTX_FIFO, # WRITE_ADDR
            len(self._hstx_line_active), # TRANS_COUNT
            self._dma_ctrl_hstx_commands, # CTRL_TRIG
        ])
        self._cb_line_pixels = array.array('I', [
            addressof(self._buffer), # READ_ADDR
            HSTX_FIFO, # WRITE_ADDR
            self._width, # TRANS_COUNT
            self._dma_ctrl_hstx_pixels, # CTRL_TRIG
        ])

        # Control blocks for restarting the dispatcher DMA. `_cb_restart_frame`
        # must be the last control block in the sequence, which causes the
        # executer to write the nested `_cb_restart_frame_nested` control block
        # back to the dispatcher DMA registers, restarting it from the beginning
        # of the control block sequence.
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

        # If the display buffer is in PSRAM, we need extra control blocks to
        # control the streamer channel and start the XIP stream. 
        if self._buffer_is_in_psram:
            # Control blocks for the streamer DMA to fill the SRAM row buffer
            # from the XIP stream FIFO. When `_cb_fill_row_buffer` is added to
            # the control block sequence, the executer will write the nested
            # `_cb_fill_row_buffer_nested` control block to the streamer DMA
            # registers, triggering it to fill the row buffer with the next row
            # of pixels from the XIP stream FIFO.
            XIP_AUX_BASE = 0x50500000
            STREAM_FIFO = XIP_AUX_BASE + 0x00
            self._cb_fill_row_buffer_nested = array.array('I', [
                STREAM_FIFO, # READ_ADDR
                addressof(self._row_buffer), # WRITE_ADDR
                self._bytes_per_row // 4, # TRANS_COUNT
                self._dma_ctrl_streamer, # CTRL_TRIG
            ])
            self._cb_fill_row_buffer = array.array('I', [
                addressof(self._cb_fill_row_buffer_nested), # READ_ADDR
                addressof(self._dma_streamer.registers), # WRITE_ADDR
                len(self._cb_fill_row_buffer_nested), # TRANS_COUNT
                self._dma_ctrl_cb_executer_nested_repeat, # CTRL_TRIG
            ])

            # Control blocks for aborting the streamer DMA, which is used in the
            # process of clearing the XIP stream FIFO after each frame. When
            # `_cb_streamer_abort` is added to the control block sequence, the
            # executer will write the nested `_cb_streamer_abort_nested` control
            # block to the CHAN_ABORT register, aborting the streamer DMA.
            DMA_BASE = 0x50000000
            CHAN_ABORT = DMA_BASE + 0x464
            self._cb_streamer_abort_nested = array.array('I', [
                1 << self._dma_streamer.channel # CHAN_ABORT
            ])
            self._cb_streamer_abort = array.array('I', [
                addressof(self._cb_streamer_abort_nested), # READ_ADDR
                CHAN_ABORT, # WRITE_ADDR
                len(self._cb_streamer_abort_nested), # TRANS_COUNT
                self._dma_ctrl_cb_executer_nested_repeat, # CTRL_TRIG
            ])

            # Control block for starting the XIP stream to read the image buffer
            # from PSRAM to the XIP stream FIFO. When `_cb_xip_stream_start` is
            # added to the control block sequence, the executer will write the
            # nested `_cb_xip_stream_start_nested` control block to the XIP
            # STREAM_ADDR and STREAM_CTR registers, starting the XIP stream.
            XIP_CTRL_BASE = 0x400C8000
            STREAM_ADDR = XIP_CTRL_BASE + 0x14
            self._cb_xip_stream_start_nested = array.array('I', [
                addressof(self._buffer), # STREAM_ADDR
                self._buffer.size, # STREAM_CTR
            ])
            self._cb_xip_stream_start = array.array('I', [
                addressof(self._cb_xip_stream_start_nested), # READ_ADDR
                STREAM_ADDR, # WRITE_ADDR
                len(self._cb_xip_stream_start_nested), # TRANS_COUNT
                self._dma_ctrl_cb_executer_nested_repeat, # CTRL_TRIG
            ])

    def _create_hstx_commands(self):
        """
        Creates the HSTX command sequences for the different line types in the
        video signal.
        """
        # The HSTX is configured to use the command expander mode. The first
        # word in the FIFO must be a command, followed by data words, followed
        # by another command, etc. Each command word consists of a 4-bit opcode
        # and a 12-bit length, packed in the 16 LSBs of the word:
        # 
        # xxxxxxxx xxxxxxxx OOOOLLLL LLLLLLLL
        # 
        # The opcodes are either RAW, where the following data words are sent
        # as-is, or TMDS, where the following data words are encoded by the
        # TMDS encoder before being sent. There are also REPEAT variants of
        # each opcode, where the next data word is repeated the specified number
        # of times.
        # 
        # The TMDS encoder can only encode pixel data. Timing data, like the
        # sync and porch signals, is sent as special TMDS control symbols using
        # RAW mode.
        # 
        # Each line is made up of a sequence of HSTX commands. There are 4
        # groups of vertical lines (front porch, sync, back porch, active
        # pixels), but the porch lines are identical, so we only need 3 unique
        # command sequences:
        # 
        # 1) Porch lines
        # 2) VSYNC lines
        # 3) Active lines

        # The TMDS control symbols from the DVI 1.0 specification:
        # https://glenwing.github.io/docs/DVI-1.0.pdf
        TMDS_CTRL_00 = 0x354
        TMDS_CTRL_01 = 0x0AB
        TMDS_CTRL_10 = 0x154
        TMDS_CTRL_11 = 0x2AB

        # Precomputed TMDS control words for different VSYNC and HSYNC states.
        # Lane 0 encodes the VSYNC and HSYNC signals, while lanes 1 and 2
        # send constant 00 control symbols during blanking intervals. The words
        # are structured with 10 bits per lane as follows:
        # 
        # (xx 2222222222 1111111111 0000000000)
        SYNC_V0_H0 = (TMDS_CTRL_00 << 20) | (TMDS_CTRL_00 << 10) | TMDS_CTRL_00
        SYNC_V0_H1 = (TMDS_CTRL_00 << 20) | (TMDS_CTRL_00 << 10) | TMDS_CTRL_01
        SYNC_V1_H0 = (TMDS_CTRL_00 << 20) | (TMDS_CTRL_00 << 10) | TMDS_CTRL_10
        SYNC_V1_H1 = (TMDS_CTRL_00 << 20) | (TMDS_CTRL_00 << 10) | TMDS_CTRL_11

        # HSTX command opcodes (RP2350 datasheet, section 12.11.5)
        HSTX_CMD_RAW         = 0x0 << 12
        HSTX_CMD_RAW_REPEAT  = 0x1 << 12
        HSTX_CMD_TMDS        = 0x2 << 12
        HSTX_CMD_TMDS_REPEAT = 0x3 << 12
        HSTX_CMD_NOP         = 0xF << 12

        # Command seqence 1 (vertical porch line)
        self._hstx_line_porch = array.array('I',[
            HSTX_CMD_RAW_REPEAT | self._H_FRONT_PORCH,
            SYNC_V1_H1, # Horizontal front porch
            HSTX_CMD_RAW_REPEAT | self._H_SYNC_WIDTH,
            SYNC_V1_H0, # Horizontal sync pulse
            HSTX_CMD_RAW_REPEAT | (self._H_BACK_PORCH + self._H_ACTIVE_PIXELS),
            SYNC_V1_H1  # Horizontal back porch + active pixels
        ])

        # Command seqence 2 (vertical sync line)
        self._hstx_line_vsync = array.array('I',[
            HSTX_CMD_RAW_REPEAT | self._H_FRONT_PORCH,
            SYNC_V0_H1, # Horizontal front porch
            HSTX_CMD_RAW_REPEAT | self._H_SYNC_WIDTH,
            SYNC_V0_H0, # Horizontal sync pulse
            HSTX_CMD_RAW_REPEAT | (self._H_BACK_PORCH + self._H_ACTIVE_PIXELS),
            SYNC_V0_H1  # Horizontal back porch + active pixels
        ])

        # Command seqence 3 (active line)
        self._hstx_line_active = array.array('I',[
            HSTX_CMD_RAW_REPEAT | self._H_FRONT_PORCH,
            SYNC_V1_H1, # Horizontal front porch
            HSTX_CMD_RAW_REPEAT | self._H_SYNC_WIDTH,
            SYNC_V1_H0, # Horizontal sync pulse
            HSTX_CMD_RAW_REPEAT | self._H_BACK_PORCH,
            SYNC_V1_H1, # Horizontal back porch
            HSTX_CMD_TMDS       | self._H_ACTIVE_PIXELS
            # Active pixels (next DMA transfer).
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

        # Add vertical front porch, synch, and back porch line control blocks.
        for row in range(self._V_FRONT_PORCH):
            self._add_control_block(self._cb_line_porch)
        for row in range(self._V_SYNC_WIDTH):
            self._add_control_block(self._cb_line_vsync)
        for row in range(self._V_BACK_PORCH):
            self._add_control_block(self._cb_line_porch)

        # Before sending the active video lines, we need to start the XIP stream
        # interface. It will end up waiting between each row of pixel data, but
        # it will happily wait until the FIFO is read out by the PSRAM DMA.
        # However, it's possible that the last frame didn't complete fully (eg.
        # the QSPI bus was busy with other higher priority transfers), leaving
        # leftover data in the FIFO (2 words deep). The FIFO needs to be cleared
        # out first, otherwise all the pixel data will be shifted by 2 words. So
        # we first initiate a dummy PSRAM DMA transfer to clear out the FIFO,
        # then immediately abort it (it will be done in 2 clock cycles, so no
        # need to wait for it), then start the XIP stream.
        if self._buffer_is_in_psram:
            self._add_control_block(self._cb_fill_row_buffer)
            self._add_control_block(self._cb_streamer_abort)
            self._add_control_block(self._cb_xip_stream_start)

        # Add active video line and pixel data control blocks.
        for row in range(self._V_ACTIVE_LINES):
            # Send the horizontal line timing data.
            self._add_control_block(self._cb_line_active)

            # If the buffer is in SRAM, we need to update the read address in
            # the pixel data control block to point to the next row of pixels.
            # However if height scaling is used, the read address repeats every
            # `_height_scale` rows.
            if not self._buffer_is_in_psram:
                self._cb_line_pixels[0] = addressof(self._buffer) + \
                    (row // self._height_scale) * (self._width * self._bytes_per_pixel)

            # If the buffer is in PSRAM, we need to start the PSRAM DMA to fill
            # the SRAM row buffer with the next row of pixel data. However if
            # height scaling is used, we only need to start the PSRAM DMA every
            # `_height_scale` rows.
            if self._buffer_is_in_psram and (row % self._height_scale) == 0:
                self._cb_line_pixels[0] = addressof(self._row_buffer)
                self._add_control_block(self._cb_fill_row_buffer)

            # Send the row of pixel data to HSTX.
            self._add_control_block(self._cb_line_pixels)

        # Restart the frame by reconfiguring the control block dispatcher DMA.
        self._add_control_block(self._cb_restart_frame)

    def _add_control_block(self, block):
        """
        Helper function to add a control block to the control block array.
        """
        # Add the control block to the array. Each control block is all 4 DMA
        # alias 0 registers in order.
        self._control_blocks[self._cb_index + 0] = block[0] # READ_ADDR
        self._control_blocks[self._cb_index + 1] = block[1] # WRITE_ADDR
        self._control_blocks[self._cb_index + 2] = block[2] # TRANS_COUNT
        self._control_blocks[self._cb_index + 3] = block[3] # CTRL_TRIG

        # Increment the control block index for the next control block.
        self._cb_index += 4

    def _start(self):
        """
        Starts the DVI output.
        """
        # Ensure the TRANS_COUNT value of the restart frame control block is set
        # to the correct value of 4. This is needed in case `_stop()` was
        # previously called, because it changes this value.
        self._control_blocks[-2] = 4

        # Activate the dispatcher. This starts the entire DMA control block
        # sequence to feed the HSTX with data to generate the DVI signal.
        self._dma_dispatcher.active(True)

    def _stop(self):
        """
        Stops the DVI output.
        """
        # The last control block is the restart frame block, which writes the
        # nested control block to the dispatcher DMA's 4 registers to restart
        # it. If we change the TRANS_COUNT from 4 to 3, the CTRL_TRIG register
        # of the dispatcher will not be written, meaning the dispatcher will not
        # be restarted, but it will still be ready to start the next frame. This
        # is a gentle way to stop all the DMAs after the current frame finishes.
        self._control_blocks[-2] = 3
