"""The code rain: the only scene this screensaver draws.

Each column is two image controls stacked on top of each other. The lower one
is the light -- a bar of colour holding the raindrops -- and it scrolls
downwards on a looping slide animation. The upper one is the stencil: black
with the column's glyphs punched out of it, and it never moves, so the light
shows through in the shape of glyphs that stay where they are.

That leaves the skin engine to move a single control per column, which is why
the rain costs nothing per frame in Python.

A variant may draw the other scene instead: the tunnel, where the rain comes at
the viewer. There a column is a narrow strip holding one raindrop, dozens of
them are on screen at once, and each has a depth of its own: the skin engine
zooms it up about the middle of the screen, which both grows it and carries it
outwards, while it falls. The same holds there -- three animations per column,
nothing per frame.

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
from render import rain, tunnel, version
from render.raindrop import column_offsets, random_float

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

#: The zoom a column enters and leaves the screen at, as a percentage of its
#: size at the screen plane.
TUNNEL_FAR, TUNNEL_NEAR = 12, 280

#: How much of the tunnel a column puts behind it in a second: Rezmason's
#: ``forwardSpeed``, which its 3d version leaves at the volumetric default of
#: a quarter. A flight therefore takes four seconds, and the speed setting
#: scales that the way it scales the rain's fall.
TUNNEL_FORWARD_SPEED = 0.25

#: Screens a column falls per second at the screen plane, per unit of the
#: variant's fall speed. The 3d version raises that speed to 0.5, which at the
#: scale below comes to a screen a second -- as against the tenth of one this
#: had before it was measured against the original.
TUNNEL_FALL_SCALE = 2.0

#: The share of its fall a column makes before it reaches the screen plane.
#: Three quarters rather than half, so most of the falling is done while the
#: column is still far off: what is left when it is close, and magnified, is
#: what could drag its top end down into the picture.
TUNNEL_FALL_LEAD = 0.75

#: Columns in the air at once, as the grid they are spread over. This is what
#: fills the screen -- the same job density does in Rezmason's volumetric
#: mode, where it multiplies the column count rather than enlarging anything.
#: They are placed on a grid and jittered inside their cell rather than
#: scattered outright: a hundred odd columns thrown at random leave holes big
#: enough to see, and the eye reads a hole as a fault rather than as chance.
TUNNEL_ACROSS, TUNNEL_DOWN = 20, 4
TUNNEL_COLUMNS = TUNNEL_ACROSS * TUNNEL_DOWN

#: Steps taken through the columns when handing out depths. Coprime with
#: their number, so every column gets a depth of its own, evenly spread
#: through the tunnel and unrelated to where the column stands -- otherwise
#: the grid would arrive as a wave sweeping across the screen.
TUNNEL_DEPTH_STEP = 47

#: Columns added for the first flight only. A looping animation can be started
#: but never joined halfway, so at the moment the tunnel appears every column
#: of the field is still at the far end, and the picture would build up over a
#: whole flight before it is full. These begin partway through a flight
#: instead, fly the rest of it once and then stay out of the way, which is
#: exactly the part of the tunnel the field has yet to fill.
TUNNEL_STARTERS_ACROSS, TUNNEL_STARTERS_DOWN = 12, 4
TUNNEL_STARTERS = TUNNEL_STARTERS_ACROSS * TUNNEL_STARTERS_DOWN

#: How far through a flight the first and the last starter begin. Neither end
#: is worth reaching: a starter beginning at the very back only doubles a
#: column the field already has out there, and one beginning at the very front
#: is gone before it can be seen.
TUNNEL_FIRST, TUNNEL_LAST = 0.08, 0.94

#: How the starters are spread across that range. Evenly, because that is how
#: the field spreads its own depths, and a starter stands in for exactly the
#: field column that has not reached that depth yet.
TUNNEL_STARTER_BIAS = 1.0

#: How far from the middle a column may sit when it passes the screen plane,
#: in screens. Beyond one it is off the picture at that moment, but it was on
#: it while it was further away, which is where the edges of the screen get
#: their columns from.
TUNNEL_SPREAD = 1.0

#: The same across the height of the screen, where it is kept shorter: a
#: column is several screens long, so it does not need spreading to cover the
#: picture, and every bit of vertical spread is length its top end has to make
#: up for -- see the height below.
TUNNEL_SPREAD_DOWN = 0.6

#: The height of one half of a column at the screen plane, in screen heights,
#: and how much that varies. Every column is a little nearer or further than
#: the zoom alone would put it, which is what keeps them from lining up in
#: shells.
#:
#: A column is drawn as two controls sharing one strip, one directly above the
#: other, because how long it is decides whether its top end can ever be seen.
#: The zoom is taken about the middle of the screen, so a top edge that sits
#: above that middle is carried further up the closer the column comes, and
#: can never enter the picture; one that sits below it is carried down into
#: view. Worst case is the lowest row of the grid at the end of its fall, so
#: the halves must come to more than the spread plus the fall between them --
#: 3.0 screens against the 2.6 that needs. A single texture cannot be that
#: long: 32 glyphs at 64 pixels is 2048, which is the limit older hardware
#: takes. Two controls of one texture cost no more memory than one, and since
#: both are zoomed about the same point they stay exactly adjacent at every
#: depth.
TUNNEL_HEIGHT = 1.5
TUNNEL_HEIGHT_SPREAD = 0.2

#: How much one column's fall may differ from the next's. The rain has to keep
#: raining while the viewer flies into it, or the drops hang in the air like a
#: photograph, and no two columns of the rain ever fell at the same rate.
TUNNEL_FALL_SPREAD = 0.35

#: The flight itself, and the whole of the perspective. Taken about the middle
#: of the screen rather than the middle of the column, a zoom does both halves
#: of what a projection does: it grows the column, and it pushes it away from
#: the vanishing point by the same factor. A column far off is therefore small
#: and near the middle; the same column close up is large and out at the edge.
#: Quadratic rather than linear, because something approaching at a steady
#: speed grows ever faster the nearer it gets, and easing in is the closest
#: the skin engine has to that.
_APPROACH = ("effect=zoom start={far} end={near} center={centre} "
             "time={duration} delay={delay} loop=true reversible=false "
             "condition=true tween=quadratic easing=in")

#: A starter's one flight: the same three effects, run once from where it
#: begins to the near end, and then left where they finish. The fade ends at
#: nothing, so a starter that has flown its flight stays invisible for as long
#: as the tunnel is up.
_STARTER = ("effect=zoom start={from_} end={near} center={centre} "
            "time={duration} reversible=false condition=true "
            "tween=quadratic easing=in")
_STARTER_FALL = ("effect=slide start=0,0 end=0,{distance} time={duration} "
                 "reversible=false condition=true tween=linear")
#: Eased in rather than evenly: a starter holds its brightness through the
#: first part of its run and gives it up late, which is what keeps the
#: picture even while the field behind it is still coming up to strength.
_STARTER_DEPTH = ("effect=fade start=100 end=0 time={duration} "
                  "reversible=false condition=true "
                  "tween=quadratic easing=in")

#: The fall. It shares the flight's period and delay, so both start over in
#: the same moment -- the one the fade below has made invisible. That is what
#: keeps the fall from needing a seam of its own.
_FALL = ("effect=slide start=0,0 end=0,{distance} time={duration} "
         "delay={delay} loop=true reversible=false condition=true "
         "tween=linear")

#: Fades a column up out of the distance and back down as it passes, so the
#: moment it jumps back to the far end happens while it is invisible. A single
#: effect cannot rise and fall, but a pulsed one runs its half forwards and
#: then backwards, which is exactly that -- and it keeps the same period as
#: the flight, so the two stay in step.
_DEPTH = ("effect=fade start=0 end=100 time={half} delay={delay} "
          "pulse=true reversible=false condition=true tween=sine")

#: The light slides down by exactly the height its pattern repeats with, so
#: the loop has no seam.
_SLIDE = ("effect=slide start=0,0 end=0,{distance} time={duration} "
          "loop=true reversible=false condition=true tween=linear")


def tunnel_zoom(phase):
    """How much a column is magnified this far through its flight.

    The skin engine's quadratic easing, as a factor rather than a percentage.
    """
    return (TUNNEL_FAR + (TUNNEL_NEAR - TUNNEL_FAR) * phase * phase) / 100.0


def tunnel_length(height, offset, fall):
    """The shortest a column may be for its top end to stay out of the picture.

    The zoom is taken about the middle of the screen, so a column whose top
    sits *d* above that middle has it drawn *d* times the zoom above it, and
    the top edge is off the picture once that reaches half the screen. What
    the top has to clear therefore changes through the flight: the fall drags
    it down, and the zoom carries it up, and the two do not cancel.

    This walks the whole flight and takes the worst moment of it. The whole
    of it, right to the end: a column of the field is as good as invisible by
    then, but a starter that begins there is at full brightness, and it is
    the same length rule that has to hold for both.
    """
    return max((offset + fall * (step / 100.0 - TUNNEL_FALL_LEAD)
                + height / 2.0 / tunnel_zoom(step / 100.0))
               for step in range(0, 101))


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

    @staticmethod
    def build(variant, on_progress=None):
        """Generate the textures of whichever scene the variant draws."""
        if variant.scene == version.SCENE_TUNNEL:
            return tunnel.generate(texture_folder(), variant, on_progress)
        return rain.generate(texture_folder(), variant, on_progress,
                             churn_sets())

    def prepare(self, variant):
        """Build a variant's textures, returning False if that is impossible."""
        try:
            self.build(variant)
        except OSError as exc:
            logger.error("Could not generate the textures: {}".format(exc))
            return False
        return True

    # -- Putting a variant on screen ---------------------------------------

    def show_variant(self, variant, on_progress=None):
        """Replace whatever is on screen with *variant*."""
        try:
            textures = self.build(variant, on_progress)
        except OSError as exc:
            logger.error("Could not generate the textures: {}".format(exc))
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
        if variant.scene == version.SCENE_TUNNEL:
            count, what = self.add_drops(variant, textures), "columns"
        else:
            count, what = self.add_columns(variant, *textures), "columns"
        set_string(LAST_VARIANT, variant.name)
        logger.info("Code rain: {} in {} {}".format(variant.name, count, what))
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

    def tunnel_seconds(self, variant):
        """Seconds one column takes from the far end to past the viewer."""
        return (self.speed_factor()
                / (TUNNEL_FORWARD_SPEED * variant.animation_speed))

    def tunnel_fall(self, variant, height):
        """Pixels a column falls over one flight, before its own variation."""
        return (height * variant.fall_speed * TUNNEL_FALL_SCALE
                * self.tunnel_seconds(variant))

    @staticmethod
    def tunnel_pose(index, across, down, columns, width, height, falls):
        """Where one column stands as it passes the screen plane.

        Its cell of the grid, jittered inside it, and the size and fall that
        go with it. Everything the flight does follows from this pose: the
        zoom about the middle of the screen carries it outwards and grows it
        by the same factor, which is what a projection does.
        """
        # The same hash the rain scatters its columns with, read at four
        # places, so a column keeps its place and its pace across runs.
        jitter_x = random_float(index, 0.0) - 0.5
        jitter_y = random_float(index, 1.0) - 0.5
        size = random_float(index, 2.0)
        pace = random_float(index, 3.0)

        fall = int(round(falls * (1 - TUNNEL_FALL_SPREAD
                                  + 2 * TUNNEL_FALL_SPREAD * pace)))

        # The spread reaches beyond the screen, because a column out there is
        # off the picture as it passes but was on it while it was further
        # away, and that is where the edges get their columns from.
        span_x = TUNNEL_SPREAD * width / float(across)
        span_y = TUNNEL_SPREAD_DOWN * height / float(down)
        place_x = (columns % across) + 0.5 + jitter_x
        place_y = (columns // across) + 0.5 + jitter_y
        offset = (place_y - down / 2.0) * span_y

        tall = int(round(height * TUNNEL_HEIGHT
                         * (1 - TUNNEL_HEIGHT_SPREAD
                            + 2 * TUNNEL_HEIGHT_SPREAD * size)))
        # Never shorter than this column needs to be where it stands and for
        # the fall it makes. Worked out rather than left to the constants
        # above, so none of their settings can quietly let a column end in
        # mid-air.
        tall = max(tall, int(tunnel_length(height, offset, fall)) + 1)
        wide = max(1, int(round(tall / float(tunnel.STRIP_ROWS))))

        left = int(round(width / 2.0 - wide / 2.0
                         + (place_x - across / 2.0) * span_x))
        # Hung most of a fall above its place, so the falling it has left
        # when it comes close is small. The pair straddles that place, which
        # puts its top a whole half above it -- far enough, with the length
        # above, that the zoom can only carry that top out of the picture.
        top = int(round(height / 2.0 - tall + offset
                        - fall * TUNNEL_FALL_LEAD))
        return left, top, wide, tall, fall

    def add_drops(self, variant, strips):
        """Fill the window with the tunnel and return how many columns it has.

        The field is the columns that stay: each flies the whole tunnel, over
        and over, and they are started a fraction of a flight apart so their
        depths spread evenly rather than arriving in shells. The starters are
        the columns that do not stay: a looping animation can be started but
        never joined halfway, so without them the field would have to build
        itself up over a whole flight before the picture was full. They begin
        partway through a flight, fly the rest of it once, and are gone.

        The stacking order stays as it is while the depths change, so a near
        column is sometimes drawn behind a far one. On a black ground with
        drops this narrow the two look the same either way.
        """
        width = self.getWidth() or FALLBACK_WIDTH
        height = self.getHeight() or FALLBACK_HEIGHT
        duration = int(round(self.tunnel_seconds(variant) * 1000))
        falls = self.tunnel_fall(variant, height)
        centre = "{},{}".format(width // 2, height // 2)
        span = TUNNEL_NEAR - TUNNEL_FAR

        controls, animations = [], []
        for index in range(TUNNEL_COLUMNS):
            left, top, wide, tall, fall = self.tunnel_pose(
                index, TUNNEL_ACROSS, TUNNEL_DOWN, index, width, height, falls)
            # Evenly spread through the tunnel, and handed out in steps across
            # the grid so depth and place stay unrelated -- the same job
            # startDepth does in the original. Without that the grid would
            # arrive as a wave sweeping over the screen.
            delay = int(round((index * TUNNEL_DEPTH_STEP % TUNNEL_COLUMNS)
                              * duration / float(TUNNEL_COLUMNS)))

            for half in range(2):
                drop = xbmcgui.ControlImage(
                    left, top + half * tall, wide, tall,
                    strips[index % len(strips)], aspectRatio=0)
                controls.append(drop)
                animations.append((drop, [
                    ("conditional", _APPROACH.format(
                        far=TUNNEL_FAR, near=TUNNEL_NEAR, centre=centre,
                        duration=duration, delay=delay)),
                    ("conditional", _FALL.format(
                        distance=fall, duration=duration, delay=delay)),
                    ("conditional", _DEPTH.format(
                        half=duration // 2, delay=delay)),
                ]))

        for number in range(TUNNEL_STARTERS):
            index = TUNNEL_COLUMNS + number
            left, top, wide, tall, fall = self.tunnel_pose(
                index, TUNNEL_STARTERS_ACROSS, TUNNEL_STARTERS_DOWN,
                number, width, height, falls)

            # How far through a flight it begins, spread across the whole of
            # one so the field is complete from the first frame
            share = ((number + 0.5) / TUNNEL_STARTERS) ** TUNNEL_STARTER_BIAS
            begun = TUNNEL_FIRST + (TUNNEL_LAST - TUNNEL_FIRST) * share
            left_to_go = int(round(duration * (1 - begun)))
            # Where the flight would have taken it by now: the zoom it has
            # reached and the fall it has made. It starts at full brightness
            # whatever its depth, rather than at the brightness that depth
            # would have: it has to carry the picture while the field behind
            # it is still filling, and the two together are what the eye sees.
            from_ = int(round(TUNNEL_FAR + span * begun * begun))

            fallen = int(round(fall * begun))
            for half in range(2):
                drop = xbmcgui.ControlImage(
                    left, top + fallen + half * tall, wide, tall,
                    strips[index % len(strips)], aspectRatio=0)
                controls.append(drop)
                animations.append((drop, [
                    ("conditional", _STARTER.format(
                        from_=from_, near=TUNNEL_NEAR, centre=centre,
                        duration=left_to_go)),
                    ("conditional", _STARTER_FALL.format(
                        distance=int(round(fall * (1 - begun))),
                        duration=left_to_go)),
                    ("conditional", _STARTER_DEPTH.format(
                        duration=left_to_go)),
                ]))

        # Added last, so it covers the columns rather than sitting behind them
        self.cover = self.new_cover(width, height, OPAQUE)
        controls.append(self.cover)

        self.addControls(controls)
        self.columns = controls
        # There are no stencils to cycle here, and the tick that would do it
        # must find nothing to work on.
        self.stencil_sets, self.churn = [], []
        for control, animation in animations:
            control.setAnimations(animation)
        return TUNNEL_COLUMNS

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
