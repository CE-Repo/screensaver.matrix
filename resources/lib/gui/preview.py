"""Loading screen shown while the video script is starting up."""

import xbmc
import xbmcgui

from core.addon import ADDON_ID, translate
from gui import skin

#: How long the preview stays up before it hands over, in seconds
HANDOVER_DELAY = 0.2


def deactivate_screensaver():
    """Ask Kodi to dismiss its own screensaver so our script can take over."""
    xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Input.ContextMenu","id":1}')


def start_video_script():
    """Launch the script entry point, which opens the real video window."""
    xbmc.executebuiltin("RunAddon({})".format(ADDON_ID))


class ScreensaverPreview(xbmcgui.WindowXMLDialog):
    """Placeholder drawn by Kodi's screensaver hook.

    A screensaver addon may only draw, not play video, so the actual playback
    happens in the script entry point. This window shows the loading screen,
    asks Kodi to deactivate the screensaver and hands over on the way out.
    """

    class ExitMonitor(xbmc.Monitor):

        def __init__(self, deactivated_callback):
            self.deactivated_callback = deactivated_callback

        def onScreensaverDeactivated(self):
            self.deactivated_callback()

    def onInit(self):
        self.exit_monitor = self.ExitMonitor(self.exit)
        self.getControl(skin.STATUS_LABEL).setLabel(translate(32013))
        self.setProperty(skin.LOADING_PROPERTY, skin.LOADING_ON)
        self.exit_monitor.waitForAbort(HANDOVER_DELAY)
        deactivate_screensaver()

    def exit(self):
        self.clearProperty(skin.LOADING_PROPERTY)
        self.close()
        start_video_script()
