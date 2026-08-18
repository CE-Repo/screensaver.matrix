"""The live code rain: a scene the addon draws instead of playing a video.

Each column is two image controls stacked on top of each other. The lower one
is the light -- a bar of colour holding the raindrops -- and it scrolls
downwards on a looping slide animation. The upper one is the stencil: black
with the column's glyphs punched out of it, and it never moves, so the light
shows through in the shape of glyphs that stay where they are.

That leaves the skin engine to move a single control per column, which is why
the rain costs nothing per frame in Python.
"""

import os
import threading

import xbmcgui

from core import logger
from core.addon import get_int, profile_folder, translate
from gui import skin
from gui.base import ScreensaverWindow
from render import rain
from render.raindrop import column_offsets

#: Folder below the addon's profile the generated textures are cached in
TEXTURE_FOLDER = "rain"

#: Milliseconds the fastest column takes to fall one screen height, at normal
#: speed. Rezmason's renderer advances a column 100 * fallSpeed (0.3) glyphs
#: per second, which over the 45 rows of the grid is one screen every 1.5
#: seconds; slower columns follow from the per-column speed the shader picks.
FALL_TIME = 1500

#: Values of the "rain-speed" setting, as factors on the time above
SPEED_FACTORS = (1.75, 1.0, 0.7, 0.5)
NORMAL_SPEED = 1

#: Used when Kodi does not report a window size
FALLBACK_WIDTH, FALLBACK_HEIGHT = 1920, 1080

#: The light slides down by exactly the height its pattern repeats with, so
#: the loop has no seam.
_SLIDE = ("effect=slide start=0,0 end=0,{distance} time={duration} "
          "loop=true reversible=false condition=true tween=linear")


def texture_folder():
    """Where the generated textures are kept between runs."""
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
            stencils, lights = rain.generate(texture_folder(), self.report_progress)
        except OSError as exc:
            logger.error("Could not generate the rain textures: {}".format(exc))
            self.show_message(32082)
            return

        if not self.active:
            return

        columns = self.add_columns(stencils, lights)
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

    def fall_time(self):
        """Milliseconds the fastest column takes to fall one screen height."""
        choice = get_int("rain-speed", default=NORMAL_SPEED)
        if not 0 <= choice < len(SPEED_FACTORS):
            choice = NORMAL_SPEED
        return FALL_TIME * SPEED_FACTORS[choice]

    def add_columns(self, stencils, lights):
        """Fill the window with columns and return how many there are."""
        width = self.getWidth() or FALLBACK_WIDTH
        height = self.getHeight() or FALLBACK_HEIGHT

        # The rain always shows the same number of glyphs from top to bottom,
        # so the columns follow from the aspect ratio: as many as fit next to
        # each other while staying square.
        count = max(1, int(round(width * rain.ROWS / float(height))))

        # How far the light travels before its pattern lines up again, and how
        # tall it has to be to cover the screen at both ends of that travel.
        travel = int(round(height * rain.PERIOD_ROWS / float(rain.ROWS)))
        fall_time = self.fall_time()

        controls, animations = [], []
        for index in range(count):
            # Derived from the window width rather than from a cell size, so
            # rounding cannot leave a gap between two columns.
            left = index * width // count
            column_width = (index + 1) * width // count - left
            texture = index % rain.COLUMN_COUNT

            light = xbmcgui.ControlImage(
                left, -travel, column_width, height + travel,
                lights[texture], aspectRatio=0)
            stencil = xbmcgui.ControlImage(
                left, 0, column_width, height,
                stencils[texture], aspectRatio=0)

            # The stencil is added after the light so it covers it; a column
            # is only ever visible through the glyphs punched out of it.
            controls.append(light)
            controls.append(stencil)
            animations.append((light, self.travel_time(fall_time, texture)))

        self.addControls(controls)
        for control, duration in animations:
            control.setAnimations([("conditional", _SLIDE.format(
                distance=travel, duration=duration))])
        return count

    @staticmethod
    def travel_time(fall_time, column):
        """Milliseconds this column's light needs for one full loop.

        The shader gives every column a speed of its own, between half and
        full, and the light has to travel several screen heights before its
        pattern repeats.
        """
        _, speed = column_offsets(column)
        return int(fall_time * rain.PERIOD_ROWS / rain.ROWS / speed)
