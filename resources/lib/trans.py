import xbmc
import xbmcgui

from .common import addon


class ScreensaverTrans(xbmcgui.WindowXMLDialog):
    class ExitMonitor(xbmc.Monitor):

        def __init__(self, activated_callback):
            self.activated_callback = activated_callback

        def onScreensaverDeactivated(self):
            self.activated_callback()

    def onInit(self):
        self.exit_monitor = self.ExitMonitor(self.exit)

    def exit(self):
        addon.setSettingBool("is_locked", False)
        self.close()

    def onAction(self, action):
        self.exit()
