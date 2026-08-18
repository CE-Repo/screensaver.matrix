"""The window that plays the Matrix videos, and the choice of what to show."""

import threading

from core import logger
from core.addon import get_int, set_bool, translate
from gui import skin
from gui.base import ScreensaverWindow, monitor
from playback.player import MatrixPlayer, is_network_source
from playback.playlist import MatrixPlaylist

#: Values of the "scene-mode" setting
SCENE_VIDEOS = 0
SCENE_LIVE = 1


class Screensaver(ScreensaverWindow):
    """Plays the shuffled playlist until the user interrupts or DPMS kicks in."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.player = None
        self.play_index = 0
        #: Filled in by whoever opens the window; built here if it was not.
        self.playlist = None

    # -- Kodi callbacks ---------------------------------------------------

    def onInit(self):
        # Kodi calls onInit again every time the window is re-created, so guard
        # against starting a second playback thread on top of the first one.
        if self.started:
            return
        self.started = True

        self.getControl(skin.STATUS_LABEL).setLabel(translate(32001))
        self.setProperty(skin.LOADING_PROPERTY, skin.LOADING_ON)

        if self.playlist is None:
            self.playlist = MatrixPlaylist().build()
        if not self.playlist:
            self.show_message(32031)
            return

        streamed = sum(1 for url in self.playlist if is_network_source(url))
        logger.info("Playlist ready: {} videos, {} streamed, {} local".format(
            len(self.playlist), streamed, len(self.playlist) - streamed))

        self.setProperty(skin.LOADING_PROPERTY, skin.LOADING_OFF)
        self.player = MatrixPlayer()
        threading.Thread(target=self.play_forever, daemon=True).start()

        self.supervise_display_timeout()

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

    def stop_scene(self):
        if self.player:
            self.player.stop()

    def pause_scene(self):
        if self.player:
            self.player.pause()


def show_screensaver():
    """Open the configured scene; blocks until the user dismisses it."""
    set_bool("is_locked", True)
    try:
        if get_int("scene-mode") == SCENE_LIVE:
            show_live_rain()
        else:
            show_videos()
    except Exception:
        # A window that never opened would otherwise leave the addon "locked",
        # and every later activation would show the empty placeholder instead.
        set_bool("is_locked", False)
        raise


def show_videos():
    """Play the video playlist, or fall back to the live rain if it is empty."""
    playlist = MatrixPlaylist().build()
    if not playlist:
        # Nothing downloaded and nothing reachable: the drawn rain needs
        # neither, so it stands in rather than leaving the screen empty.
        logger.info("No videos to play, showing the live code rain instead")
        show_live_rain()
        return

    skin.show_modal(Screensaver, skin.SCREENSAVER_XML,
                    lambda window: setattr(window, "playlist", playlist))


def show_live_rain():
    """Draw the code rain, which needs no video file at all."""
    # Imported here so the video path never pays for the renderer.
    from gui.rain import RainScreensaver
    skin.show_modal(RainScreensaver, skin.RAIN_XML)
