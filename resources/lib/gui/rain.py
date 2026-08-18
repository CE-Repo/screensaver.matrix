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
the change itself is immediate, and a black cover is faded over the picture
while it happens.
"""

import os
import random
import threading
import time

import xbmcgui

from core import logger
from core.addon import (get_bool, get_int, get_string, profile_folder, set_bool,
                        set_string, translate)
from gui import skin
from gui.base import ScreensaverWindow, monitor
from render import rain, version
from render.raindrop import column_offsets

#: Folder below the addon's profile the generated textures are cached in
TEXTURE_FOLDER = "rain"

#: Values of the "rain-speed" setting, as factors on the version's own speed
SPEED_FACTORS = (1.75, 1.0, 0.7, 0.5)
NORMAL_SPEED = 1

#: Columns swapped to their next set of glyphs per second, and how often the
#: swapping is done. In the original every glyph changes about twice a second;
#: a texture holds a whole column, so this changes a handful of glyphs at a
#: time in one column instead, which is as close as a texture gets.
CHURN_PER_SECOND = 8
TICK_SECONDS = 0.25

#: Minutes a variant stays up before the next one takes over. Zero means it
#: stays for as long as the screensaver is up.
DEFAULT_INTERVAL = 5
FOREVER = 0

#: Remembers across runs which variant was shown last. A screensaver starts
#: over every time the user touches something, and without this the same
#: variant could come up again straight away.
LAST_VARIANT = "last-variant"

#: Used when Kodi does not report a window size
FALLBACK_WIDTH, FALLBACK_HEIGHT = 1920, 1080

#: How long the picture takes to fade out, and again to fade back in, when the
#: variant changes -- and in how many steps. The skin engine cannot be asked to
#: run this for us: its animations react to conditions rather than to a moment
#: we choose, so the cover is dimmed from here instead. Two dozen steps over
#: two thirds of a second is smooth and costs two dozen calls.
FADE_MILLISECONDS = 700
FADE_STEPS = 24

#: The alpha the cover is drawn at, covering everything and covering nothing.
#: "Nothing" is one rather than zero on purpose: Kodi skips a diffuse colour
#: of zero when it builds a control, so a cover left at zero would come back
#: as plain black if the window were ever rebuilt. One is invisible either way.
OPAQUE, CLEAR = 255, 1

#: The light slides down by exactly the height its pattern repeats with, so
#: the loop has no seam.
_SLIDE = ("effect=slide start=0,0 end=0,{distance} time={duration} "
          "loop=true reversible=false condition=true tween=linear")


def texture_folder():
    """Where the generated textures are kept between runs."""
    return os.path.join(profile_folder(), TEXTURE_FOLDER)


def churn_sets():
    """How many sets of glyphs a column may be swapped between."""
    return rain.CHURN_SETS if get_bool("rain-churn", default=True) else 1


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
        #: The controls of the variant currently on screen, cover included
        self.columns = []
        #: The black cover the variant change happens behind
        self.cover = None
        #: Every column's stencil, which texture it draws and which set that
        #: texture came from, so the glyphs can be cycled
        self.churn = []
        self.stencil_sets = []

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
        # Textures of variants this addon no longer has are of no use to
        # anyone. The ones merely switched off are left alone: switching one
        # back on should not mean building it again.
        rain.drop_folders(texture_folder(),
                          set(known.name for known in version.VERSIONS))

        variants = enabled_versions()
        upcoming = self.in_random_order(get_string(LAST_VARIANT))

        if not self.show_variant(next(upcoming), self.report_progress):
            return
        self.setProperty(skin.LOADING_PROPERTY, skin.LOADING_OFF)
        if len(variants) < 2 or self.interval() == FOREVER:
            # Nothing to change to, but the glyphs still have to keep cycling,
            # so the tick carries on for as long as the window is up.
            self.hold(float("inf"))
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
    def in_random_order(previous=None):
        """Yield the enabled variants, reshuffled after every pass.

        Drawing one at random every time is the obvious thing to do and the
        wrong one: with four variants it lands on the one already showing
        every fourth pick, sometimes three or four times over, while another
        stays away for ages. A shuffled pass gives every variant its turn
        before any repeats.

        That leaves one place a variant could still run twice -- where two
        passes meet -- so a pass that would open on the one just shown swaps
        it with another. *previous* carries that across screensaver runs.
        """
        while True:
            order = enabled_versions()
            random.shuffle(order)
            if len(order) > 1 and order[0].name == previous:
                other = random.randrange(1, len(order))
                order[0], order[other] = order[other], order[0]
            for variant in order:
                previous = variant.name
                yield variant

    def interval(self):
        """Seconds a variant stays up, ``FOREVER`` when it should not change."""
        minutes = get_int("rain-interval", default=DEFAULT_INTERVAL)
        return max(FOREVER, minutes) * 60

    def hold(self, seconds):
        """Wait, cycling glyphs as we go, until the time is up."""
        waited = 0.0
        while self.active and waited < seconds:
            if monitor.waitForAbort(TICK_SECONDS):
                return False
            waited += TICK_SECONDS
            self.cycle_glyphs()
        return self.active

    def cycle_glyphs(self):
        """Swap a few columns to their next set of glyphs."""
        if len(self.stencil_sets) < 2:
            return
        for _ in range(max(1, int(round(CHURN_PER_SECOND * TICK_SECONDS)))):
            column = random.choice(self.churn)
            column[2] = (column[2] + 1) % len(self.stencil_sets)
            try:
                column[0].setImage(self.stencil_sets[column[2]][column[1]])
            except Exception as exc:
                # The window may be closing; there is nothing left to cycle.
                logger.debug("Could not cycle a column: {}".format(exc))
                return

    def prepare(self, variant):
        """Build a variant's textures, returning False if that is impossible."""
        try:
            rain.generate(texture_folder(), variant, sets=churn_sets())
        except OSError as exc:
            logger.error("Could not generate the rain textures: {}".format(exc))
            return False
        return True

    # -- Putting a variant on screen ---------------------------------------

    def show_variant(self, variant, on_progress=None):
        """Replace whatever is on screen with *variant*."""
        try:
            stencils, lights = rain.generate(
                texture_folder(), variant, on_progress, churn_sets())
        except OSError as exc:
            logger.error("Could not generate the rain textures: {}".format(exc))
            self.show_message(32082)
            return False

        if not self.active:
            return False

        # Whatever is on screen goes behind the cover first. The very first
        # variant has nothing to hide, and simply fades up out of the black.
        if self.cover is not None and not self.fade(CLEAR, OPAQUE):
            return False

        # Everything goes, cover included, so the new cover can be added last
        # and end up on top. The window's own backdrop is black as well, so
        # the moment in between looks no different.
        self.clear_columns()
        columns = self.add_columns(variant, stencils, lights)
        set_string(LAST_VARIANT, variant.name)
        logger.info("Code rain: {} in {} columns".format(variant.name, columns))
        return self.fade(OPAQUE, CLEAR)

    def fade(self, first, last):
        """Take the cover from one alpha to the other, smoothly."""
        if self.cover is None:
            return self.active
        for step in range(1, FADE_STEPS + 1):
            share = step / float(FADE_STEPS)
            # Eased at both ends, so the change does not start or stop abruptly
            eased = share * share * (3 - 2 * share)
            try:
                self.cover.setColorDiffuse(
                    "{:02X}000000".format(int(round(first + (last - first) * eased))))
            except Exception as exc:
                # The window may be closing; there is nothing left to fade.
                logger.debug("Could not fade the cover: {}".format(exc))
                return False
            if monitor.waitForAbort(FADE_MILLISECONDS / 1000.0 / FADE_STEPS):
                return False
            if not self.active:
                return False
        return True

    def pause_scene(self):
        """Take the columns off the screen when the display is switched off.

        Kodi processes and renders only the controls that are visible, so
        hiding them is what actually stops the work; the window itself stays
        up, which is the point of pausing rather than stopping.
        """
        for control in self.columns:
            try:
                control.setVisible(False)
            except Exception as exc:
                logger.debug("Could not hide a column: {}".format(exc))

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
        self.cover = None
        self.churn = []

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
        """Fill the window with a variant and return how many columns it has."""
        width = self.getWidth() or FALLBACK_WIDTH
        height = self.getHeight() or FALLBACK_HEIGHT
        shape = rain.geometry(variant)

        # How far the light travels before its pattern lines up again, and how
        # long that takes at the speed the variant sets.
        travel = int(round(height * shape.period_rows / float(shape.rows)))
        loop = self.fall_time(variant, shape) * self.speed_factor() \
            * shape.period_rows / shape.rows

        # The rain always shows the same number of glyphs from top to bottom,
        # so the columns follow from the aspect ratio: as many as fit next to
        # each other while keeping the shape of a cell.
        count = max(1, int(round(width * shape.rows
                                 * variant.glyph_height_to_width / float(height))))

        self.stencil_sets = stencils
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
                stencils[0][texture], aspectRatio=0)
            self.churn.append([stencil, texture, 0])

            # The stencil is added after the light so it covers it; a column
            # is only ever visible through the glyphs punched out of it.
            controls.append(light)
            controls.append(stencil)
            # Every column falls at a speed of its own, between half and full,
            # the way the shader picks it.
            _, speed = column_offsets(texture)
            animations.append((light, [("conditional", _SLIDE.format(
                distance=travel, duration=int(loop / speed)))]))

        # Added last, so it covers the columns rather than sitting behind them
        self.cover = self.new_cover(width, height, OPAQUE)
        controls.append(self.cover)

        self.addControls(controls)
        self.columns = controls
        for control, animation in animations:
            control.setAnimations(animation)
        return count

    # -- The cover ---------------------------------------------------------

    def new_cover(self, width, height, alpha):
        """A black sheet the size of the screen, at the given alpha."""
        return xbmcgui.ControlImage(
            0, 0, width, height, skin.BLACK_TEXTURE, aspectRatio=0,
            colorDiffuse="{:02X}000000".format(alpha))


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
