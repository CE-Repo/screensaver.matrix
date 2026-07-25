import json
import threading
import time

import xbmc
import xbmcgui

from .common import translate, addon, addon_path
from .offline import offline
from .playlist import MatrixPlaylist
from .trans import ScreensaverTrans

monitor = xbmc.Monitor()

LOG_PREFIX = "[Matrix Screensaver]"


def is_network_source(path):
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
        xbmc.log("{} Requesting {} source: {}".format(
            LOG_PREFIX, "network" if is_network_source(path) else "local", path),
            level=xbmc.LOGINFO)
        self.play(path, windowed=True)

    def onAVStarted(self):
        if self.requested_at is None:
            return
        delay = time.time() - self.requested_at
        self.requested_at = None
        xbmc.log("{} First frame after {:.2f}s, {}".format(
            LOG_PREFIX, delay,
            "streamed over the network" if is_network_source(self.source) else "read from disk"),
            level=xbmc.LOGINFO)

    def onPlayBackError(self):
        xbmc.log("{} Playback failed for {}".format(LOG_PREFIX, self.source), level=xbmc.LOGERROR)


class Screensaver(xbmcgui.WindowXML):

    def __init__(self, *args, **kwargs):
        self.DPMStime = json.loads(xbmc.executeJSONRPC(
            '{"jsonrpc":"2.0","method":"Settings.GetSettingValue","params":{"setting":"powermanagement.displaysoff"},"id":2}'))[
                            'result']['value'] * 60
        self.isDPMSactive = bool(self.DPMStime > 0)
        self.active = True
        self.matrixplayer = None
        self.video_playlist = MatrixPlaylist().compute_playlist_array()
        xbmc.log(msg=f"kodi dpms time: {self.DPMStime}", level=xbmc.LOGDEBUG)
        xbmc.log(msg=f"kodi dpms active: {self.isDPMSactive}", level=xbmc.LOGDEBUG)

    def onInit(self):
        self.getControl(32502).setLabel(translate(32001))
        self.setProperty("screensaver-matrix-loading", "true")

        if self.video_playlist:
            streamed = len([url for url in self.video_playlist if is_network_source(url)])
            xbmc.log("{} Playlist ready: {} videos, {} streamed, {} local".format(
                LOG_PREFIX, len(self.video_playlist), streamed, len(self.video_playlist) - streamed),
                level=xbmc.LOGINFO)

            self.setProperty("screensaver-matrix-loading", "false")
            self.matrixplayer = MatrixPlayer()

            # Start player thread
            threading.Thread(target=self.start_playback).start()

            # DPMS logic
            self.max_allowed_time = None

            if self.isDPMSactive and addon.getSettingInt("check-dpms") == 1:
                self.max_allowed_time = self.DPMStime

            elif addon.getSettingInt("check-dpms") == 2:
                self.max_allowed_time = addon.getSettingInt("manual-dpms") * 60

            xbmc.log(msg=f"check dpms: {addon.getSetting('check-dpms')}",
                     level=xbmc.LOGDEBUG)
            xbmc.log(msg=f"before supervision: {self.max_allowed_time}",
                     level=xbmc.LOGDEBUG)

            if self.max_allowed_time:
                delta = 0
                while self.active:
                    if delta >= self.max_allowed_time:
                        self.activateDPMS()
                        break
                    monitor.waitForAbort(1)
                    delta += 1
        else:
            self.novideos()

    def activateDPMS(self):
        xbmc.log(msg="[Matrix Screensaver] Manually activating DPMS!", level=xbmc.LOGDEBUG)
        self.active = False

        # Take action on the video
        enable_window_placeholder = False
        if addon.getSettingInt("dpms-action") == 0:
            self.matrixplayer.pause()
        else:
            self.clearAll()
            enable_window_placeholder = True

        if addon.getSettingBool("toggle-displayoff") or addon.getSettingBool("toggle-cecoff"):
            monitor.waitForAbort(1)

        if addon.getSettingBool("toggle-displayoff"):
            try:
                xbmc.executebuiltin('ToggleDPMS')
            except Exception as e:
                xbmc.log(msg=f"[Matrix Screensaver] Failed to toggle DPMS: {e}",
                         level=xbmc.LOGDEBUG)

        if addon.getSetting("toggle-cecoff") == "true":
            try:
                xbmc.executebuiltin('CECStandby')
            except Exception as e:
                xbmc.log(msg=f"[Matrix Screensaver] Failed to toggle device off via CEC: {e}",
                         level=xbmc.LOGDEBUG)

        # Enable placeholder window
        if enable_window_placeholder:
            self.toTransparent()

    def novideos(self):
        self.setProperty("screensaver-matrix-loading", "false")
        self.getControl(32503).setLabel(translate(32031))
        self.getControl(32503).setVisible(True)

    @classmethod
    def toTransparent(self):
        trans = ScreensaverTrans(
            'screensaver-matrix-trans.xml',
            addon_path,
            'default',
            '',
        )
        trans.doModal()
        xbmc.sleep(100)
        del trans

    def clearAll(self, close=True):
        self.active = False
        if self.matrixplayer:
            self.matrixplayer.stop()
        self.close()

    def onAction(self, action):
        addon.setSettingBool("is_locked", False)
        self.clearAll()

    def start_playback(self):
        self.playindex = 0
        self.matrixplayer.play_video(self.video_playlist[self.playindex])
        while self.active and not monitor.abortRequested():
            monitor.waitForAbort(1)
            # If we finish playing the video
            if not self.matrixplayer.isPlaying() and self.active:
                # Increment the iterator used to access the array or reset to 0
                if self.playindex < len(self.video_playlist) - 1:
                    self.playindex += 1
                else:
                    self.playindex = 0
                # Using the updated iterator, start playing the next video
                self.matrixplayer.play_video(self.video_playlist[self.playindex])


def run(params=False):
    if not params:
        addon.setSettingBool("is_locked", True)
        screensaver = Screensaver(
            'screensaver-matrix.xml',
            addon_path,
            'default',
            '',
        )
        screensaver.doModal()
        xbmc.sleep(100)
        del screensaver

    else:
        # Params existed or was true when calling run(), so download files locally
        offline()
