"""The code rain: the only scene this screensaver draws.

Each column is two image controls stacked on top of each other. The lower one
is the light -- a bar of colour holding the raindrops -- and it scrolls
downwards on a looping slide animation. The upper one is the stencil: black
with the column's glyphs punched out of it, and it never moves, so the light
shows through in the shape of glyphs that stay where they are.

That leaves the skin engine to move a single control per column, which is why
the rain costs nothing per frame in Python.

The variants the user leaves switched on take turns: one is picked at random,
held for the configured while, and then swapped for the next one. The textures
of the variant coming up are built while the current one is still on screen, so
the change itself is immediate.
"""

import os
import random
import threading
import time

import xbmcgui

from core import logger
from core.addon import get_bool, get_int, profile_folder, set_bool, translate
from gui import skin
from gui.base import ScreensaverWindow, monitor
from render import rain, version
from render.raindrop import column_offsets

#: Folder below the addon's profile the generated textures are cached in
TEXTURE_FOLDER = "rain"

#: Values of the "rain-speed" setting, as factors on the version's own speed
SPEED_FACTORS = (1.75, 1.0, 0.7, 0.5)
NORMAL_SPEED = 1

#: Minutes a variant stays up before the next one takes over
DEFAULT_INTERVAL = 5

#: Used when Kodi does not report a window size
FALLBACK_WIDTH, FALLBACK_HEIGHT = 1920, 1080

#: The light slides down by exactly the height its pattern repeats with, so
#: the loop has no seam.
_SLIDE = ("effect=slide start=0,0 end=0,{distance} time={duration} "
          "loop=true reversible=false condition=true tween=linear")


def texture_folder():
    """Where the generated textures are kept between runs."""
    return os.path.join(profile_folder(), TEXTURE_FOLDER)


def enabled_versions():
    """The variants that are switched on, in the order they are listed."""
    chosen = [variant for variant in version.VERSIONS
              if get_bool(variant.setting_id, default=variant.enabled)]
    if not chosen:
        # Every variant switched off would leave an empty screen, which is
        # never what the user meant by starting a screensaver.
        logger.info("No variant is switched on, drawing {} instead".format(
            version.DEFAULT_VERSION.name))
        return [version.DEFAULT_VERSION]
    return chosen


def stripe_tint(variant, column, columns):
    """The colour a striped version paints this column in, as a Kodi diffuse.

    A version with stripes draws its light white and is tinted here instead,
    which keeps the stripes spread across however many columns the screen
    happens to have. Everything else is left alone.
    """
    if not variant.stripes:
        return ""
    # The original spreads its stripe colours across the screen and blends
    # between them, so the position lands between two of them.
    position = (column + 0.5) / columns * len(variant.stripes) - 0.5
    position = max(0.0, min(len(variant.stripes) - 1.0, position))
    low = int(position)
    high = min(low + 1, len(variant.stripes) - 1)
    share = position - low
    return "FF" + "".join(
        "{:02X}".format(int(round(start + (end - start) * share)))
        for start, end in zip(variant.stripes[low], variant.stripes[high]))


class RainScreensaver(ScreensaverWindow):
    """Draws one variant after another until the user interrupts or DPMS hits."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #: The controls of the variant currently on screen
        self.columns = []

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
        threading.Thread(target=self.run_scene, daemon=True).start()

        self.supervise_display_timeout()

    # -- Taking turns ------------------------------------------------------

    def run_scene(self):
        """Show one variant after another for as long as the window is up."""
        variants = enabled_versions()
        upcoming = self.in_random_order()

        if not self.show_variant(next(upcoming), self.report_progress):
            return
        self.setProperty(skin.LOADING_PROPERTY, skin.LOADING_OFF)
        if len(variants) < 2:
            return

        shown_at = time.monotonic()
        while self.active:
            variant = next(upcoming)
            # Built while the current variant is still on screen, so the
            # change itself costs nothing. Cached runs return at once.
            if not self.prepare(variant):
                return
            if not self.hold(self.interval() - (time.monotonic() - shown_at)):
                return
            if not self.show_variant(variant):
                return
            shown_at = time.monotonic()

    @staticmethod
    def in_random_order():
        """Yield the enabled variants, reshuffled after every pass.

        Drawing at random on its own would repeat variants and skip others for
        a long while; a shuffled pass keeps it varied without either.
        """
        while True:
            order = enabled_versions()
            random.shuffle(order)
            for variant in order:
                yield variant

    def interval(self):
        """Seconds a variant stays up."""
        return max(1, get_int("rain-interval", default=DEFAULT_INTERVAL)) * 60

    def hold(self, seconds):
        """Wait, returning False if the window closed while we did."""
        waited = 0
        while self.active and waited < seconds:
            if monitor.waitForAbort(1):
                return False
            waited += 1
        return self.active

    def prepare(self, variant):
        """Build a variant's textures, returning False if that is impossible."""
        try:
            rain.generate(texture_folder(), variant)
        except OSError as exc:
            logger.error("Could not generate the rain textures: {}".format(exc))
            return False
        return True

    # -- Putting a variant on screen ---------------------------------------

    def show_variant(self, variant, on_progress=None):
        """Replace whatever is on screen with *variant*."""
        try:
            stencils, lights = rain.generate(
                texture_folder(), variant, on_progress)
        except OSError as exc:
            logger.error("Could not generate the rain textures: {}".format(exc))
            self.show_message(32082)
            return False

        if not self.active:
            return False

        self.clear_columns()
        columns = self.add_columns(variant, stencils, lights)
        logger.info("Code rain: {} in {} columns".format(variant.name, columns))
        return True

    def clear_columns(self):
        """Take the current variant off the screen."""
        if not self.columns:
            return
        try:
            self.removeControls(self.columns)
        except Exception as exc:
            # The window may be closing; the controls go with it either way.
            logger.debug("Could not remove the previous columns: {}".format(exc))
        self.columns = []

    def report_progress(self, done, total):
        """Show how far the one-off texture generation has come."""
        try:
            self.getControl(skin.STATUS_LABEL).setLabel(
                "{} ({}/{})".format(translate(32081), done, total))
        except Exception:
            # The window may already be gone; the generation itself is cheap
            # enough to let it finish and populate the cache.
            pass

    def speed_factor(self):
        """How much the speed setting stretches the version's own pace."""
        choice = get_int("rain-speed", default=NORMAL_SPEED)
        if not 0 <= choice < len(SPEED_FACTORS):
            choice = NORMAL_SPEED
        return SPEED_FACTORS[choice]

    @staticmethod
    def fall_time(variant, shape):
        """Milliseconds the fastest column takes to fall one screen height.

        The shader advances a column by ``100 * fallSpeed`` glyphs per second,
        so how long a screen takes follows from how many rows it holds.
        """
        glyphs_per_second = 100.0 * variant.fall_speed * variant.animation_speed
        return 1000.0 * shape.rows / glyphs_per_second

    def add_columns(self, variant, stencils, lights):
        """Fill the window with columns and return how many there are."""
        width = self.getWidth() or FALLBACK_WIDTH
        height = self.getHeight() or FALLBACK_HEIGHT
        shape = rain.geometry(variant)

        # The rain always shows the same number of glyphs from top to bottom,
        # so the columns follow from the aspect ratio: as many as fit next to
        # each other while keeping the shape of a cell.
        count = max(1, int(round(width * shape.rows
                                 * variant.glyph_height_to_width / float(height))))

        # How far the light travels before its pattern lines up again, and how
        # tall it has to be to cover the screen at both ends of that travel.
        travel = int(round(height * shape.period_rows / float(shape.rows)))
        loop = self.fall_time(variant, shape) * self.speed_factor() \
            * shape.period_rows / shape.rows

        controls, animations = [], []
        for index in range(count):
            # Derived from the window width rather than from a cell size, so
            # rounding cannot leave a gap between two columns.
            left = index * width // count
            column_width = (index + 1) * width // count - left
            texture = index % rain.COLUMN_COUNT

            light = xbmcgui.ControlImage(
                left, -travel, column_width, height + travel,
                lights[texture], aspectRatio=0,
                colorDiffuse=stripe_tint(variant, index, count))
            stencil = xbmcgui.ControlImage(
                left, 0, column_width, height,
                stencils[texture], aspectRatio=0)

            # The stencil is added after the light so it covers it; a column
            # is only ever visible through the glyphs punched out of it.
            controls.append(light)
            controls.append(stencil)
            # Every column falls at a speed of its own, between half and full,
            # the way the shader picks it.
            _, speed = column_offsets(texture)
            animations.append((light, int(loop / speed)))

        self.addControls(controls)
        self.columns = controls
        for control, duration in animations:
            control.setAnimations([("conditional", _SLIDE.format(
                distance=travel, duration=duration))])
        return count


def show_screensaver():
    """Open the rain window; blocks until the user dismisses the screensaver."""
    set_bool("is_locked", True)
    try:
        skin.show_modal(RainScreensaver, skin.RAIN_XML)
    except Exception:
        # A window that never opened would otherwise leave the addon "locked",
        # and every later activation would show the empty placeholder instead.
        set_bool("is_locked", False)
        raise
