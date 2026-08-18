"""Screensaver hook (xbmc.ui.screensaver): decides what Kodi gets to see.

Kodi closes a screensaver window as soon as it deactivates the screensaver, so
this entry point draws nothing lasting itself -- it hands over to the script
entry point, which opens the window the rain runs in.
"""

import os
import sys

import xbmc

# Kodi only puts this file's own directory on sys.path, so resources/lib has to
# be added before anything below it can be imported.
_LIB_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _LIB_PATH not in sys.path:
    sys.path.insert(0, _LIB_PATH)

from core.addon import get_bool, notification, translate
from gui import skin
from gui.preview import ScreensaverPreview, deactivate_screensaver, start_rain_script
from gui.transparent import ScreensaverTrans


def main():
    if xbmc.getCondVisibility("Player.HasMedia"):
        # Something else is playing; get out of the way instead of covering it.
        deactivate_screensaver()
        return

    if get_bool("is_locked"):
        # Our own window is already up, so show the transparent placeholder
        # rather than starting the rain a second time.
        skin.show_modal(ScreensaverTrans, skin.TRANSPARENT_XML)
        return

    if get_bool("show-notifications"):
        notification(translate(32000), translate(32010))

    if get_bool("show-previewwindow"):
        skin.show_modal(ScreensaverPreview, skin.SCREENSAVER_XML)
    else:
        # Hand over straight away, without drawing the loading screen first.
        start_rain_script()
        deactivate_screensaver()


if __name__ == "__main__":
    main()
