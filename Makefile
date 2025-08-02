ifndef PORT_DIR
$(error PORT_DIR not specified. Use 'make PORT_DIR=~/micropython/ports/rp2' or similar.)
endif

ifeq ($(findstring rp2,$(PORT_DIR)),rp2)
# Set Pico SDK flags to use the MicroPython OpenCV malloc wrapper functions and
# enable C++ exceptions
CMAKE_ARGS += -DSKIP_PICO_MALLOC=1 -DPICO_CXX_ENABLE_EXCEPTIONS=1
endif

# Get current directory
CURRENT_DIR = $(shell pwd)

# Ensure we're building the Red Vision board variant
MAKE_ARGS += BOARD_VARIANT=RED_VISION

# Set the MicroPython user C module path to the OpenCV module
MAKE_ARGS = USER_C_MODULES="$(CURRENT_DIR)/micropython-opencv/micropython_opencv.cmake"

# Use the Red Vision driver manifest
MAKE_ARGS += FROZEN_MANIFEST="$(CURRENT_DIR)/manifest.py"

# Build MicroPython with the OpenCV module
all:
	@cd $(PORT_DIR) && export CMAKE_ARGS="$(CMAKE_ARGS)" && make -f Makefile $(MAKEFLAGS) $(MAKE_ARGS)

# Clean the MicroPython build
clean:
	@cd $(PORT_DIR) && make -f Makefile $(MAKEFLAGS) $(MAKE_ARGS) clean

# Load the MicroPython submodules
submodules:
	@cd $(PORT_DIR) && make -f Makefile $(MAKEFLAGS) $(MAKE_ARGS) submodules
