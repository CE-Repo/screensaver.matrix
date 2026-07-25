"""Script entry point (xbmc.python.script): plays the videos or downloads them.

Called without arguments by the screensaver hook, and with "offline" by the
"Download Videos" button in the addon settings.
"""

import os
import sys

# Kodi only puts this file's own directory on sys.path, so resources/lib has to
# be added before anything below it can be imported.
_LIB_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _LIB_PATH not in sys.path:
    sys.path.insert(0, _LIB_PATH)

from core import logger

#: Argument settings.xml passes to open the download dialog
DOWNLOAD_COMMAND = "offline"


def main(argv):
    command = argv[1] if len(argv) > 1 else ""

    if not command:
        from gui.screensaver import show_screensaver
        show_screensaver()
        return

    if command != DOWNLOAD_COMMAND:
        logger.warning("Unknown argument '{}', opening the downloader".format(command))
    from download.picker import download_videos
    download_videos()


if __name__ == "__main__":
    main(sys.argv)
