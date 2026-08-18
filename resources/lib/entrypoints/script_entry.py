"""Script entry point (xbmc.python.script): draws the code rain.

A screensaver addon may only draw a window of its own, and Kodi tears that
window down again as soon as it is dismissed. The rain runs from here instead,
where it can hold the screen for as long as the user leaves it alone.
"""

import os
import sys

# Kodi only puts this file's own directory on sys.path, so resources/lib has to
# be added before anything below it can be imported.
_LIB_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _LIB_PATH not in sys.path:
    sys.path.insert(0, _LIB_PATH)


def main():
    from gui.rain import show_screensaver
    show_screensaver()


if __name__ == "__main__":
    main()
