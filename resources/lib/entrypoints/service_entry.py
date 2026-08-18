"""Background service (xbmc.service): resets the lock flag once per Kodi start."""

import os
import sys

# Kodi only puts this file's own directory on sys.path, so resources/lib has to
# be added before anything below it can be imported.
_LIB_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _LIB_PATH not in sys.path:
    sys.path.insert(0, _LIB_PATH)

from core.addon import set_bool

if __name__ == "__main__":
    # "is_locked" survives a crash and would then make every screensaver
    # activation show the empty placeholder instead of the rain.
    set_bool("is_locked", False)
