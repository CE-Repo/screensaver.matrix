"""Empty full-screen window used as a placeholder while a video is running."""

import xbmc
import xbmcgui

from core.addon import set_bool


class ScreensaverTrans(xbmcgui.WindowXMLDialog):
    """Invisible window shown when Kodi activates the screensaver again.

    Our own video is already playing at that point, so instead of restarting it
    this window just occupies the screen until the user presses something.
    """

    class ExitMonitor(xbmc.Monitor):

        def __init__(self, deactivated_callback):
            self.deactivated_callback = deactivated_callback

        def onScreensaverDeactivated(self):
            self.deactivated_callback()

    def onInit(self):
        self.exit_monitor = self.ExitMonitor(self.exit)

    def exit(self):
        set_bool("is_locked", False)
        self.close()

    def onAction(self, action):
        self.exit()
