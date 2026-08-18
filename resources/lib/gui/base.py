"""What the screensaver windows have in common.

A window here fills the screen until the user presses something, and hands the
display over to the power management once the configured timeout expires. What
is on it is up to the window, which the two hooks at the bottom cover.
"""

import json

import xbmc
import xbmcgui

from core import logger
from core.addon import get_bool, get_int, set_bool, translate
from gui import skin
from gui.transparent import ScreensaverTrans

#: Values of the "check-dpms" setting
DPMS_OFF = 0
DPMS_FROM_KODI = 1
DPMS_MANUAL = 2

#: Values of the "dpms-action" setting
DPMS_ACTION_PAUSE = 0

_DISPLAYS_OFF_REQUEST = (
    '{"jsonrpc":"2.0","method":"Settings.GetSettingValue",'
    '"params":{"setting":"powermanagement.displaysoff"},"id":1}'
)

monitor = xbmc.Monitor()


def kodi_displays_off_seconds():
    """Kodi's own "turn the display off after" timeout in seconds, 0 if unset."""
    try:
        response = json.loads(xbmc.executeJSONRPC(_DISPLAYS_OFF_REQUEST))
        return int(response["result"]["value"]) * 60
    except (ValueError, KeyError, TypeError) as exc:
        logger.warning("Could not read Kodi's display timeout: {}".format(exc))
        return 0


def run_builtin(command):
    """Run a Kodi built-in, logging instead of raising if it is unavailable."""
    try:
        xbmc.executebuiltin(command)
    except Exception as exc:
        logger.error("Built-in '{}' failed: {}".format(command, exc))


class ScreensaverWindow(xbmcgui.WindowXML):
    """Full-screen window that runs until the user or the display timeout ends it."""

    def __init__(self, *args, **kwargs):
        self.active = True
        self.started = False
        self.kodi_dpms_seconds = kodi_displays_off_seconds()
        logger.debug("Kodi display timeout: {}s".format(self.kodi_dpms_seconds))

    # -- Kodi callbacks ---------------------------------------------------

    def onAction(self, action):
        set_bool("is_locked", False)
        self.stop()

    # -- Lifetime ---------------------------------------------------------

    def stop(self):
        """End the scene and close the window."""
        self.active = False
        self.stop_scene()
        self.close()

    def show_message(self, string_id):
        """Replace the loading screen with a single line of text."""
        self.setProperty(skin.LOADING_PROPERTY, skin.LOADING_OFF)
        message = self.getControl(skin.MESSAGE_LABEL)
        message.setLabel(translate(string_id))
        message.setVisible(True)

    # -- Display power management -----------------------------------------

    def display_timeout(self):
        """Seconds to keep playing before the display is switched off, 0 = never."""
        mode = get_int("check-dpms")
        if mode == DPMS_FROM_KODI:
            return self.kodi_dpms_seconds
        if mode == DPMS_MANUAL:
            return get_int("manual-dpms") * 60
        return 0

    def supervise_display_timeout(self):
        """Block until the configured timeout expires or the window is closed."""
        timeout = self.display_timeout()
        logger.debug("Display supervision: {}s".format(timeout))
        if timeout <= 0:
            return

        waited = 0
        while self.active and waited < timeout:
            if monitor.waitForAbort(1):
                return
            waited += 1

        if self.active:
            self.activate_dpms()

    def activate_dpms(self):
        """Stop or pause the scene and put the display to sleep."""
        logger.debug("Display timeout reached, activating DPMS")
        self.active = False

        # Pausing keeps this window up; stopping tears it down and leaves the
        # transparent placeholder behind so Kodi still counts as idle.
        show_placeholder = get_int("dpms-action") != DPMS_ACTION_PAUSE
        if show_placeholder:
            self.stop()
        else:
            self.pause_scene()

        turn_display_off = get_bool("toggle-displayoff")
        standby_via_cec = get_bool("toggle-cecoff")

        if turn_display_off or standby_via_cec:
            # Give the player a moment to release the display before the
            # hardware is told to switch off.
            monitor.waitForAbort(1)

        if turn_display_off:
            run_builtin("ToggleDPMS")
        if standby_via_cec:
            run_builtin("CECStandby")

        if show_placeholder:
            skin.show_modal(ScreensaverTrans, skin.TRANSPARENT_XML)

    # -- Hooks ------------------------------------------------------------

    def stop_scene(self):
        """Called before the window closes. Nothing to do for a drawn scene."""

    def pause_scene(self):
        """Called instead of stopping when DPMS is set to pause the scene."""
