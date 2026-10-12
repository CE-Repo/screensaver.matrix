"""Screensaver hook (xbmc.ui.screensaver): decides what Kodi gets to see.

Kodi closes a screensaver window as soon as it deactivates the screensaver, so
this entry point draws nothing lasting itself -- it hands over to the script
entry point, which opens the window the rain runs in. See gui/launch.py.
"""

import os
import sys

# Kodi only puts this file's own directory on sys.path, so resources/lib has to
# be added before anything below it can be imported.
_LIB_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _LIB_PATH not in sys.path:
    sys.path.insert(0, _LIB_PATH)

from gui import launch  # noqa: E402

if __name__ == "__main__":
    launch.screensaver()
