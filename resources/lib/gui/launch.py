"""What the two entry points in addon.xml do, kept out of them.

Kodi's addon checker wants an entry point to do little more than hand over,
so everything that decides something lives here.
"""

import xbmc

from core import logger
from core.addon import get_bool, is_locked, notification, translate
from gui import skin
from gui.preview import ScreensaverPreview, deactivate_screensaver, start_rain_script
from gui.transparent import ScreensaverTrans

#: Argument settings.xml passes to build the textures ahead of time
PREPARE_COMMAND = "prepare"


def screensaver():
    """The screensaver hook: decide what Kodi gets to see, then hand over."""
    if xbmc.getCondVisibility("Player.HasMedia"):
        # Something else is playing; get out of the way instead of covering it.
        deactivate_screensaver()
        return

    if is_locked():
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


def script(argv):
    """The script: draw the rain, or build the textures when asked to."""
    command = argv[1] if len(argv) > 1 else ""

    if not command:
        from gui.rain import show_screensaver
        show_screensaver()
        return

    if command != PREPARE_COMMAND:
        logger.warning("Unknown argument '{}', preparing the textures".format(command))
    from gui.prepare import prepare_textures
    prepare_textures()
