"""Script entry point (xbmc.python.script): draws the code rain.

A screensaver addon may only draw a window of its own, and Kodi tears that
window down again as soon as it is dismissed. The rain runs from here instead,
where it can hold the screen for as long as the user leaves it alone.

Called without arguments by the screensaver hook, and with "prepare" by the
button in the addon settings that builds every variant's textures up front.
"""

import os
import sys

# Kodi only puts this file's own directory on sys.path, so resources/lib has to
# be added before anything below it can be imported.
_LIB_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _LIB_PATH not in sys.path:
    sys.path.insert(0, _LIB_PATH)

from core import logger

#: Argument settings.xml passes to build the textures ahead of time
PREPARE_COMMAND = "prepare"


def main(argv):
    command = argv[1] if len(argv) > 1 else ""

    if not command:
        from gui.rain import show_screensaver
        show_screensaver()
        return

    if command != PREPARE_COMMAND:
        logger.warning("Unknown argument '{}', preparing the textures".format(command))
    from gui.prepare import prepare_textures
    prepare_textures()


if __name__ == "__main__":
    main(sys.argv)
