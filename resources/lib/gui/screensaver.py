"""The window that plays the Matrix videos."""

import json
import threading

import xbmc
import xbmcgui

from core import logger
from core.addon import get_bool, get_int, set_bool, translate
from gui import skin
from gui.transparent import ScreensaverTrans
from playback.player import MatrixPlayer, is_network_source
from playback.playlist import MatrixPlaylist

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


class Screensaver(xbmcgui.WindowXML):
    """Plays the shuffled playlist until the user interrupts or DPMS kicks in."""

    def __init__(self, *args, **kwargs):
        self.active = True
        self.started = False
        self.player = None
        self.play_index = 0
        self.playlist = MatrixPlaylist().build()
        self.kodi_dpms_seconds = kodi_displays_off_seconds()
        logger.debug("Kodi display timeout: {}s".format(self.kodi_dpms_seconds))

    # -- Kodi callbacks ---------------------------------------------------

    def onInit(self):
        # Kodi calls onInit again every time the window is re-created, so guard
        # against starting a second playback thread on top of the first one.
        if self.started:
            return
        self.started = True

        self.getControl(skin.STATUS_LABEL).setLabel(translate(32001))
        self.setProperty(skin.LOADING_PROPERTY, skin.LOADING_ON)

        if not self.playlist:
            self.show_no_videos()
            return

        streamed = sum(1 for url in self.playlist if is_network_source(url))
        logger.info("Playlist ready: {} videos, {} streamed, {} local".format(
            len(self.playlist), streamed, len(self.playlist) - streamed))

        self.setProperty(skin.LOADING_PROPERTY, skin.LOADING_OFF)
        self.player = MatrixPlayer()
        threading.Thread(target=self.play_forever, daemon=True).start()

        self.supervise_display_timeout()

    def onAction(self, action):
        set_bool("is_locked", False)
        self.stop()

    # -- Playback ---------------------------------------------------------

    def play_forever(self):
        """Loop over the playlist until the window closes or Kodi shuts down."""
        self.player.play_video(self.playlist[self.play_index])
        while self.active:
            if monitor.waitForAbort(1):
                break
            # Nothing playing means the previous video ran out; move on.
            if self.active and not self.player.isPlaying():
                self.play_index = (self.play_index + 1) % len(self.playlist)
                self.player.play_video(self.playlist[self.play_index])

    def stop(self):
        """Stop playback and close the window."""
        self.active = False
        if self.player:
            self.player.stop()
        self.close()

    def show_no_videos(self):
        self.setProperty(skin.LOADING_PROPERTY, skin.LOADING_OFF)
        message = self.getControl(skin.MESSAGE_LABEL)
        message.setLabel(translate(32031))
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
        """Stop or pause the video and put the display to sleep."""
        logger.debug("Display timeout reached, activating DPMS")
        self.active = False

        # Pausing keeps this window up; stopping tears it down and leaves the
        # transparent placeholder behind so Kodi still counts as idle.
        show_placeholder = get_int("dpms-action") != DPMS_ACTION_PAUSE
        if show_placeholder:
            self.stop()
        elif self.player:
            self.player.pause()

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


def show_screensaver():
    """Open the video window; blocks until the user dismisses the screensaver."""
    set_bool("is_locked", True)
    try:
        skin.show_modal(Screensaver, skin.SCREENSAVER_XML)
    except Exception:
        # A window that never opened would otherwise leave the addon "locked",
        # and every later activation would show the empty placeholder instead.
        set_bool("is_locked", False)
        raise
