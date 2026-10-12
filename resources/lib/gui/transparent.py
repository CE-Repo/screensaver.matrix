"""Empty full-screen window used as a placeholder while the rain is running."""

import xbmcgui

from core.addon import set_locked
from gui.skin import ExitMonitor


class ScreensaverTrans(xbmcgui.WindowXMLDialog):
    """Invisible window shown when Kodi activates the screensaver again.

    Our own window is already up at that point, so instead of starting over
    this one just occupies the screen until the user presses something.
    """

    def onInit(self):
        self.exit_monitor = ExitMonitor(self.exit)

    def exit(self):
        set_locked(False)
        self.close()

    def onAction(self, action):
        self.exit()
