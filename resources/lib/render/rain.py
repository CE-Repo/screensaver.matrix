"""Builds the two textures each column of the code rain is made of.

Rezmason's renderer keeps its glyphs in a fixed grid and moves only the
brightness down through them. Kodi cannot light single glyphs, but it can
stack two images, and that is enough to do the same thing the other way round:

* the **light** is a narrow bar of colour, one band per grid row, that scrolls
  down behind everything else. It carries the raindrops -- the trails, their
  bright cursors, the black between them -- and nothing else.
* the **stencil** lies on top of it and does not move. It is black, with the
  column's glyphs punched out of it, so the light is only ever visible in the
  shape of a glyph.

The glyphs therefore stay exactly where they are while the light travels
through them, which is the whole point.

Every version of the rain brings its own grid, its own glyphs and its own
raindrop length, so the shape of both textures is worked out per version and
they are cached in a folder of their own.

Nothing in here talks to Kodi, so the textures can be generated and inspected
outside of it as well.
"""

import os
import shutil
from collections import namedtuple
from random import Random

from render import glyphs, raindrop
from render.png import write_rgba

#: The screen the column counts in the version table are given for
REFERENCE_ASPECT = 16.0 / 9.0

#: Screens of travel a light texture should last before it repeats itself
TARGET_LOOP_SCREENS = 8

#: Cycles one loop may hold. Fewer than two would make every raindrop in a
#: column the same length again; more than six buys nothing.
MIN_CYCLES, MAX_CYCLES = 2, 6

#: What older graphics hardware still accepts as a texture size
MAX_TEXTURE = 2048

#: Texture pixels per grid row in the light bar. The brightness is constant
#: within a row, so this only decides how sharp the step between two rows stays
#: once Kodi has stretched the texture.
MIN_ROW_PIXELS, MAX_ROW_PIXELS = 2, 8

#: Two pixels wide rather than one: a single column of pixels is an odd thing
#: to hand a graphics driver, and the second one costs nothing.
LIGHT_WIDTH = 2

#: Textures generated per kind. Enough for every column of an ultra-wide
#: screen to get its own, because two columns sharing one would run the same
#: glyphs and the same raindrops side by side.
COLUMN_COUNT = 112

#: Sets of stencils a column can be swapped between, and the share of its
#: glyphs that changes from one set to the next. Swapping a column to the next
#: set changes a handful of its glyphs and leaves the rest where they are,
#: which is what the glyphs cycling in the original looks like.
CHURN_SETS = 3
CHURN_SHARE = 0.15

#: Raised whenever the shape of the textures changes, so old files in the
#: cache folder are not mistaken for current ones.
CACHE_VERSION = 6

#: Fixed seed for the glyph choice: the textures are cached on disk, and a
#: stable seed means the same addon version always produces the same files.
_SEED = 0x4D4154

_PREFIXES = ("stencil-", "light-", "rain-")

#: Everything about a version's textures that follows from its settings
Geometry = namedtuple("Geometry", (
    "rows",          # glyphs from the top of the screen to the bottom
    "cell_width",    # texture pixels per glyph
    "cell_height",
    "cycles",        # raindrops one texture loop holds
    "period_rows",   # rows the light repeats itself with
    "light_rows",    # rows the light texture holds altogether
    "row_pixels",    # texture pixels per row of the light
))


def geometry(version):
    """Work out the shape of one version's textures."""
    rows = max(4, int(round(
        version.columns / (REFERENCE_ASPECT * version.glyph_height_to_width))))
    cell_width = glyphs.CELL_WIDTH
    cell_height = max(1, int(round(cell_width * version.glyph_height_to_width)))

    cycle = raindrop.cycle_rows(version)
    # Long raindrops need fewer cycles per loop, or the light would have to
    # travel dozens of screens -- and be far too tall a texture -- before it
    # lines up with itself again.
    wanted = min(MAX_CYCLES, max(MIN_CYCLES,
                                 int(round(TARGET_LOOP_SCREENS * rows / float(cycle)))))
    cycles, light_rows, row_pixels = wanted, 0, 0
    while cycles >= MIN_CYCLES:
        light_rows = cycle * cycles + rows
        row_pixels = min(MAX_ROW_PIXELS, MAX_TEXTURE // light_rows)
        if row_pixels >= MIN_ROW_PIXELS:
            break
        cycles -= 1
    else:
        # Nothing fits: keep the shortest loop and give up some sharpness.
        cycles = MIN_CYCLES
        light_rows = cycle * cycles + rows
        row_pixels = max(1, MAX_TEXTURE // light_rows)

    return Geometry(rows, cell_width, cell_height,
                    cycles, cycle * cycles, light_rows, row_pixels)


def version_folder(folder, version):
    """Each version caches its textures in a folder of its own."""
    return os.path.join(folder, version.name)


def _stencil_name(index, shape, group):
    return "stencil-v{}-{}x{}-{:03d}-{}.png".format(
        CACHE_VERSION, shape.cell_width, shape.cell_height, index, group)


def _light_name(index, shape):
    return "light-v{}-{}x{}-{:03d}.png".format(
        CACHE_VERSION, shape.row_pixels, shape.light_rows, index)


def texture_paths(folder, version, sets=CHURN_SETS):
    """Where one version's textures live, existing or not.

    The stencils come as *sets* lists of one texture per column; the lights are
    one list, because a column's raindrops do not change when its glyphs do.
    """
    shape = geometry(version)
    inside = version_folder(folder, version)
    stencils = [[os.path.join(inside, _stencil_name(index, shape, group))
                 for index in range(COLUMN_COUNT)]
                for group in range(max(1, sets))]
    lights = [os.path.join(inside, _light_name(index, shape))
              for index in range(COLUMN_COUNT)]
    return stencils, lights


def drop_folders(folder, keep):
    """Delete the cached textures of variants that are not in *keep*.

    Returns the names of the variants that were dropped.
    """
    dropped = []
    if not os.path.isdir(folder):
        return dropped
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if name in keep or not os.path.isdir(path):
            continue
        try:
            shutil.rmtree(path)
            dropped.append(name)
        except OSError:
            # A leftover we cannot delete costs disk space and nothing else.
            pass
    return dropped


def _drop_stale(folder, current):
    """Delete textures an earlier version of the addon left behind."""
    keep = set(os.path.basename(path) for path in current)
    for name in os.listdir(folder):
        if name.startswith(_PREFIXES) and name not in keep:
            try:
                os.remove(os.path.join(folder, name))
            except OSError:
                # A leftover we cannot delete costs disk space and nothing
                # else, so it must not stop the rain from starting.
                pass


def _write(path, width, height, scanlines):
    """Write a texture, but only move it into place once it is complete."""
    partial = path + ".part"
    write_rgba(partial, width, height, scanlines)
    os.replace(partial, path)


class _Punch:
    """Turns each glyph into the hole it leaves in a stencil, once."""

    #: Only the alpha channel carries the glyph, inverted, so a covered pixel
    #: is a hole and an empty one stays opaque.
    _INVERT = bytes(255 - value for value in range(256))

    def __init__(self, coverage_maps, shape, background):
        self.coverage_maps = coverage_maps
        self.shape = shape
        self.background = background
        self.rows = {}

    def get(self, glyph):
        rows = self.rows.get(glyph)
        if rows is None:
            coverage = self.coverage_maps[glyph]
            pixels = len(coverage)
            buffer = bytearray(pixels * 4)
            for channel, value in enumerate(self.background):
                buffer[channel::4] = bytes((value,)) * pixels
            buffer[3::4] = coverage.translate(self._INVERT)
            stride = self.shape.cell_width * 4
            rows = [bytes(buffer[line * stride:(line + 1) * stride])
                    for line in range(self.shape.cell_height)]
            self.rows[glyph] = rows
        return rows


def _sequences(random, glyph_count, shape, sets):
    """The glyph in every cell of a column, once per set of stencils.

    The first set is rolled at random; each one after it takes the set before
    it and rolls a share of its cells again.
    """
    sequence = [random.randrange(glyph_count) for _ in range(shape.rows)]
    sequences = [sequence]
    changes = max(1, int(round(shape.rows * CHURN_SHARE)))
    for _ in range(sets - 1):
        sequence = list(sequence)
        for cell in random.sample(range(shape.rows), changes):
            sequence[cell] = random.randrange(glyph_count)
        sequences.append(sequence)
    return sequences


def _stencil(punch, sequence):
    """One column of glyphs, as the scanlines of a stencil texture."""
    scanlines = []
    for glyph in sequence:
        scanlines.extend(punch.get(glyph))
    return scanlines


def _light(column, version, shape):
    """One column's raindrops, as the scanlines of a light texture.

    The rows are generated from the bottom of the grid upwards, the way the
    shader counts them, and written out top to bottom.
    """
    colours = raindrop.column_colours(
        shape.light_rows, column, shape.light_rows - 1, version, shape.cycles)
    scanlines = []
    for red, green, blue in colours:
        band = bytes((red, green, blue, 255)) * LIGHT_WIDTH
        scanlines.extend([band] * shape.row_pixels)
    return scanlines


def generate(folder, version, on_progress=None, sets=CHURN_SETS):
    """Write every missing texture of *version* and return their paths.

    *on_progress* is called with the number of textures done and the total,
    so the caller can drive a progress display while this runs.
    """
    shape = geometry(version)
    inside = version_folder(folder, version)
    os.makedirs(inside, exist_ok=True)
    stencils, lights = texture_paths(folder, version, sets)
    every = [path for group in stencils for path in group] + lights
    _drop_stale(inside, every)

    missing = [path for path in every if not os.path.exists(path)]
    if not missing:
        return stencils, lights

    outstanding = set(missing)
    total = len(missing)
    done = 0
    punch = None

    for index in range(COLUMN_COUNT):
        wanted = [group for group in range(len(stencils))
                  if stencils[group][index] in outstanding]
        if wanted:
            if punch is None:
                # The background of a stencil is the colour the palette holds
                # where nothing is lit, which is black for every version but
                # the one that draws dark glyphs on a light page.
                background = raindrop.colour(0.0, False, version)
                punch = _Punch(glyphs.load(version.atlas, shape.cell_width,
                                           shape.cell_height,
                                           version.glyph_edge_crop),
                               shape, background)
            # Seeded per column, so an interrupted run resumes with the same
            # textures it would have written the first time, and so a set
            # added later still matches the ones already on disk.
            sequences = _sequences(Random(_SEED + index),
                                   len(punch.coverage_maps), shape, len(stencils))
            for group in wanted:
                _write(stencils[group][index], shape.cell_width,
                       shape.rows * shape.cell_height,
                       _stencil(punch, sequences[group]))
                done += 1
                if on_progress:
                    on_progress(done, total)

        if lights[index] in outstanding:
            _write(lights[index], LIGHT_WIDTH,
                   shape.light_rows * shape.row_pixels,
                   _light(index, version, shape))
            done += 1
            if on_progress:
                on_progress(done, total)

    return stencils, lights
