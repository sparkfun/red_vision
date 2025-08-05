# Include the board's original manifest file
include("$(BOARD_DIR)/manifest.py")

# Include the Red Vision directory as one package
package("red_vision")

# Ensure the SD card module is included
require("sdcard")

# Check if the examples directory has been archived
import os
try:
    os.stat('extract_red_vision_examples.py')

    # If we get here, then the examples directory has been archived and we can
    # add it to the manifest so it gets frozen into the firmware
    module("extract_red_vision_examples.py")

    # Also freeze the boot script that automatically unpacks the examples
    module("boot.py")
except OSError:
    # The examples directory has not been archived, nothing to do
    pass
