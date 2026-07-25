"""The player used for the screensaver videos."""

import time

import xbmc

from core import logger


def is_network_source(path):
    """True when *path* is streamed rather than read from local storage."""
    return bool(path) and path.startswith(("http://", "https://"))


class MatrixPlayer(xbmc.Player):
    """Player that reports where each video came from and how fast it started.

    The delay between asking for playback and the first rendered frame tells
    streaming and buffering apart: a streamed video starts within seconds, while
    a player that first has to pull the whole file needs minutes for the same
    video. These lines are logged at info level, so no debug logging is needed.
    """

    def __init__(self):
        super().__init__()
        self.source = None
        self.requested_at = None

    def play_video(self, path):
        self.source = path
        self.requested_at = time.time()
        logger.info("Requesting {} source: {}".format(
            "network" if is_network_source(path) else "local", path))
        self.play(path, windowed=True)

    def onAVStarted(self):
        if self.requested_at is None:
            return
        delay = time.time() - self.requested_at
        self.requested_at = None
        logger.info("First frame after {:.2f}s, {}".format(
            delay,
            "streamed over the network" if is_network_source(self.source)
            else "read from disk"))

    def onPlayBackError(self):
        self.requested_at = None
        logger.error("Playback failed for {}".format(self.source))
