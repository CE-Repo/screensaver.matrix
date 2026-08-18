"""The live code rain: a scene the addon draws instead of playing a video.

The columns are plain image controls carrying the textures from
``render.rain``, and each one is given a looping slide animation. From then on
the skin engine moves them, so the rain runs at the skin's frame rate without
any per-frame work in Python.
"""

import os
import random
import threading

import xbmcgui

from core import logger
from core.addon import get_int, profile_folder, translate
from gui import skin
from gui.base import ScreensaverWindow
from render import rain

#: Folder below the addon's profile the generated textures are cached in
TEXTURE_FOLDER = "rain"

#: Milliseconds a column takes to fall one screen height, at normal speed.
#: Taken from Rezmason's renderer: its columns advance 100 * fallSpeed (0.3)
#: glyphs per second, scaled per column by a random 0.5 to 1.0, which over the
#: 45 rows of the grid works out as one screen height every 1.5 to 3 seconds.
MIN_FALL_TIME, MAX_FALL_TIME = 1500, 3000

#: Values of the "rain-speed" setting, as factors on the times above
SPEED_FACTORS = (1.75, 1.0, 0.7, 0.5)
NORMAL_SPEED = 1

#: How much single columns may be dimmed, which gives the rain some depth
MIN_BRIGHTNESS, MAX_BRIGHTNESS = 0.62, 1.0

#: Used when Kodi does not report a window size
FALLBACK_WIDTH, FALLBACK_HEIGHT = 1920, 1080

#: The animation slides a column down by exactly one screen height, which is
#: the height the texture repeats itself with, so the loop has no seam.
_SLIDE = ("effect=slide start=0,0 end=0,{distance} time={duration} "
          "loop=true reversible=false condition=true tween=linear")


def texture_folder():
    """Where the generated column textures are kept between runs."""
    return os.path.join(profile_folder(), TEXTURE_FOLDER)


class RainScreensaver(ScreensaverWindow):
    """Draws falling glyph columns until the user interrupts or DPMS kicks in."""

    def onInit(self):
        # Kodi calls onInit again whenever the window is re-created; the
        # columns are already in place by then.
        if self.started:
            return
        self.started = True

        self.getControl(skin.STATUS_LABEL).setLabel(translate(32081))
        self.setProperty(skin.LOADING_PROPERTY, skin.LOADING_ON)

        # Generating the textures takes a moment on the very first run and
        # must not block the window while the loading screen is up.
        threading.Thread(target=self.build_scene, daemon=True).start()

        self.supervise_display_timeout()

    # -- Building the scene ------------------------------------------------

    def build_scene(self):
        try:
            textures = rain.generate(texture_folder(), self.report_progress)
        except OSError as exc:
            logger.error("Could not generate the rain textures: {}".format(exc))
            self.show_message(32082)
            return

        if not self.active:
            return

        columns = self.add_columns(textures)
        logger.info("Code rain running with {} columns".format(columns))
        self.setProperty(skin.LOADING_PROPERTY, skin.LOADING_OFF)

    def report_progress(self, done, total):
        """Show how far the one-off texture generation has come."""
        try:
            self.getControl(skin.STATUS_LABEL).setLabel(
                "{} ({}/{})".format(translate(32081), done, total))
        except Exception:
            # The window may already be gone; the generation itself is cheap
            # enough to let it finish and populate the cache.
            pass

    def fall_times(self):
        """The range of milliseconds a column may take to fall, as configured."""
        choice = get_int("rain-speed", default=NORMAL_SPEED)
        if not 0 <= choice < len(SPEED_FACTORS):
            choice = NORMAL_SPEED
        factor = SPEED_FACTORS[choice]
        return int(MIN_FALL_TIME * factor), int(MAX_FALL_TIME * factor)

    def add_columns(self, textures):
        """Fill the window with animated columns and return how many there are."""
        width = self.getWidth() or FALLBACK_WIDTH
        height = self.getHeight() or FALLBACK_HEIGHT
        fastest, slowest = self.fall_times()

        # The rain always shows the same number of glyphs from top to bottom,
        # so the columns follow from the aspect ratio: as many as fit next to
        # each other while staying square.
        count = max(1, int(round(width * rain.ROWS / float(height))))

        # Every column gets a texture of its own where possible: two columns
        # sharing one would scroll the same glyphs and give the trick away.
        order = list(range(len(textures)))
        random.shuffle(order)

        controls = []
        for index in range(count):
            # Derived from the window width rather than from the cell size, so
            # rounding cannot leave a gap between two columns.
            left = index * width // count
            right = (index + 1) * width // count
            brightness = random.uniform(MIN_BRIGHTNESS, MAX_BRIGHTNESS)
            controls.append(xbmcgui.ControlImage(
                left, -height, right - left, height * 2,
                textures[order[index % len(order)]],
                aspectRatio=0,
                colorDiffuse="{:02X}FFFFFF".format(int(round(255 * brightness)))))

        self.addControls(controls)
        for control in controls:
            control.setAnimations([("conditional", _SLIDE.format(
                distance=height,
                duration=random.randint(fastest, slowest)))])
        return count
