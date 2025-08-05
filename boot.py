# Check whether `restore_examples.txt` exists
import os
try:
    os.stat('red_vision_examples/restore_examples.txt')
    # If this succeeds, the file exists, so we don't need to do anything
except OSError:
    # If we get here, it means the file doesn't exist, so we should unpack the
    # examples folder and create the file
    import extract_red_vision_examples
    file = open('red_vision_examples/restore_examples.txt', 'w')
    file.write('''Hi!

This folder is frozen into the firmware. To make it accessible, a special
boot.py script that's also frozen into the firmware automatically unpacks the
frozen folder to an editable location on the filesystem. It will only unpack the
folder if this `restore_examples.txt` file is missing, so you can safely edit
the examples here without your changes being overwritten. If you want to restore
the examples to their original state, delete this file and reboot your board.
''')
    file.close()

    # Clean up to avoid cluttering the namespace
    del extract_red_vision_examples, file

# The examples folder has an importable module, so we need to add it to the path
import sys
sys.path.append('red_vision_examples')

# Clean up to avoid cluttering the namespace
del os, sys
