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

Nothing in here talks to Kodi, so the textures can be generated and inspected
outside of it as well.
"""

import os
from random import Random

from render import glyphs, raindrop
from render.png import write_rgba

#: Glyphs per screen height. 45 rows put 80 columns on a 16:9 screen, the grid
#: Rezmason's renderer uses by default.
ROWS = 45

#: Edge length of one glyph in the stencil textures
CELL = glyphs.CELL

#: Height of a stencil: the full screen, one glyph per row
STENCIL_HEIGHT = ROWS * CELL

#: Rows the light texture repeats itself with, and how many it holds. The
#: control it belongs to is one screen taller than the repeat, so that it
#: covers the screen at both ends of its travel.
PERIOD_ROWS = raindrop.CYCLE_ROWS * raindrop.CYCLES_PER_LOOP
LIGHT_ROWS = PERIOD_ROWS + ROWS

#: Texture pixels per grid row in the light bar. The brightness is constant
#: within a row, so this only decides how sharp the step between two rows
#: stays once Kodi has stretched the texture; four keeps the whole texture
#: below the 2048 pixel limit of older graphics hardware.
ROW_PIXELS = 4
LIGHT_HEIGHT = LIGHT_ROWS * ROW_PIXELS

#: Two pixels wide rather than one: a single column of pixels is an odd thing
#: to hand a graphics driver, and the second one costs nothing.
LIGHT_WIDTH = 2

#: Textures generated per kind. Enough for every column of an ultra-wide
#: screen to get its own, because two columns sharing one would run the same
#: glyphs and the same raindrops side by side.
COLUMN_COUNT = 112

#: Raised whenever the shape of the textures changes, so old files in the
#: cache folder are not mistaken for current ones.
CACHE_VERSION = 4

#: Fixed seed for the glyph choice: the textures are cached on disk, and a
#: stable seed means the same addon version always produces the same files.
_SEED = 0x4D4154

#: "rain-" is the name older versions cached their textures under, and is
#: listed so those are cleaned out too.
_PREFIXES = ("stencil-", "light-", "rain-")


def _stencil_name(index):
    return "stencil-v{}-{}-{:03d}.png".format(CACHE_VERSION, CELL, index)


def _light_name(index):
    return "light-v{}-{}-{:03d}.png".format(CACHE_VERSION, ROW_PIXELS, index)


def texture_paths(folder):
    """Where the stencil and light textures live, existing or not."""
    stencils = [os.path.join(folder, _stencil_name(index))
                for index in range(COLUMN_COUNT)]
    lights = [os.path.join(folder, _light_name(index))
              for index in range(COLUMN_COUNT)]
    return stencils, lights


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

    #: Black everywhere; only the alpha channel carries the glyph, inverted,
    #: so a covered pixel is a hole and an empty one stays opaque.
    _INVERT = bytes(255 - value for value in range(256))

    def __init__(self, coverage_maps):
        self.coverage_maps = coverage_maps
        self.rows = {}

    def get(self, glyph):
        rows = self.rows.get(glyph)
        if rows is None:
            coverage = self.coverage_maps[glyph]
            buffer = bytearray(len(coverage) * 4)
            buffer[3::4] = coverage.translate(self._INVERT)
            stride = CELL * 4
            rows = [bytes(buffer[line * stride:(line + 1) * stride])
                    for line in range(CELL)]
            self.rows[glyph] = rows
        return rows


def _stencil(punch, random, glyph_count):
    """One column of glyphs, as the scanlines of a stencil texture."""
    scanlines = []
    for _ in range(ROWS):
        scanlines.extend(punch.get(random.randrange(glyph_count)))
    return scanlines


def _light(column):
    """One column's raindrops, as the scanlines of a light texture.

    The rows are generated from the bottom of the grid upwards, the way the
    shader counts them, and written out top to bottom.
    """
    colours = raindrop.column_colours(LIGHT_ROWS, column, LIGHT_ROWS - 1)
    scanlines = []
    for red, green, blue in colours:
        band = bytes((red, green, blue, 255)) * LIGHT_WIDTH
        scanlines.extend([band] * ROW_PIXELS)
    return scanlines


def generate(folder, on_progress=None):
    """Write every missing texture into *folder* and return their paths.

    *on_progress* is called with the number of textures done and the total,
    so the caller can drive a progress display while this runs.
    """
    os.makedirs(folder, exist_ok=True)
    stencils, lights = texture_paths(folder)
    _drop_stale(folder, stencils + lights)

    missing = [path for path in stencils + lights if not os.path.exists(path)]
    if not missing:
        return stencils, lights

    outstanding = set(missing)
    total = len(missing)
    done = 0
    punch = None

    for index in range(COLUMN_COUNT):
        if stencils[index] in outstanding:
            if punch is None:
                punch = _Punch(glyphs.load())
            # Seeded per column, so an interrupted run resumes with the same
            # textures it would have written the first time.
            random = Random(_SEED + index)
            _write(stencils[index], CELL, STENCIL_HEIGHT,
                   _stencil(punch, random, len(punch.coverage_maps)))
            done += 1
            if on_progress:
                on_progress(done, total)

        if lights[index] in outstanding:
            _write(lights[index], LIGHT_WIDTH, LIGHT_HEIGHT, _light(index))
            done += 1
            if on_progress:
                on_progress(done, total)

    return stencils, lights
