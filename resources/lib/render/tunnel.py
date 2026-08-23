"""The strips of the 3D tunnel: one raindrop each, on a transparent ground.

Rezmason's project draws its volumetric mode as a grid of quads rather than one
picture: every column of the rain is a quad of its own, it starts at a depth of
its own -- ``quadDepth = fract(startDepth + time * forwardSpeed)`` in
``rainPass.vert.glsl`` -- and it travels towards the camera on its own, over and
over. What fills the screen is the number of columns, not the size of any one
of them.

This module builds those columns. A strip is one narrow texture holding one
raindrop: dim at the tail, brightest at the head, transparent everywhere else,
so the strips behind it show through. The window then puts many of them on
screen at once, each at its own place and its own depth, and lets the skin
engine fly them past. A handful of strips is enough for that -- what a column
looks like matters far less than how many of them are in the air -- so they are
generated once and shared out.

Nothing in here talks to Kodi, so the strips can be generated and inspected
outside of it as well.
"""

import os
from random import Random

from render import glyphs, rain, raindrop
from render.png import write_rgba

#: The glyphs one strip holds, and the texture pixels per glyph. 32 cells of
#: 64 pixels come to 64 x 768: small enough to keep dozens of them in memory,
#: large enough that a strip close to the viewer still has detail.
STRIP_ROWS = 32
CELL = 64

#: Strips to draw from. The window puts far more columns than this on screen
#: and shares the strips out between them; at a glance no two columns near
#: each other run the same glyphs anyway, because they are at different
#: depths and different heights.
STRIPS = 36

#: The share of a strip's cells left empty. A solid column of glyphs looks
#: printed; a few holes in it look like rain.
GAPS = 0.16

#: The brightness along a drop, from the tail up to the glyph below the head.
#: Kept off the dark end: a strip is a still image, and a glyph the palette
#: draws black would simply be a hole in it.
MIN_LIGHT, MAX_LIGHT = 0.35, 0.85

#: Raised whenever the shape of the strips changes, so old files in the cache
#: folder are not mistaken for current ones.
CACHE_VERSION = 3

#: Fixed seed, so the same addon version always produces the same strips
_SEED = 0x33445459

#: What a file in the tunnel's cache folder may be called. "sheet-" is
#: retired -- the tunnel was built from full-screen sheets before it was built
#: from columns -- and is listed so those files are cleared out rather than
#: left behind for good.
_PREFIX = "strip-"
_PREFIXES = (_PREFIX, "sheet-")

#: One row of an empty cell: transparent, and therefore all zeroes
_EMPTY_ROW = bytes(CELL * 4)


def _strip_name(index):
    return "{}v{}-{}x{}-{:02d}.png".format(
        _PREFIX, CACHE_VERSION, CELL, STRIP_ROWS * CELL, index)


def strip_paths(folder, variant):
    """Where one variant's strips live, existing or not."""
    inside = rain.version_folder(folder, variant)
    return [os.path.join(inside, _strip_name(index)) for index in range(STRIPS)]


def _drop_stale(folder, current):
    """Delete strips an earlier version of the addon left behind."""
    keep = set(os.path.basename(path) for path in current)
    for name in os.listdir(folder):
        if name.startswith(_PREFIXES) and name not in keep:
            try:
                os.remove(os.path.join(folder, name))
            except OSError:
                # A leftover we cannot delete costs disk space and nothing
                # else, so it must not stop the tunnel from starting.
                pass


def _cell(coverage, colour):
    """One glyph as the rows of a cell: its colour, carried by its coverage."""
    pixels = len(coverage)
    buffer = bytearray(pixels * 4)
    for channel, value in enumerate(colour):
        buffer[channel::4] = bytes((value,)) * pixels
    buffer[3::4] = coverage
    stride = CELL * 4
    return [bytes(buffer[line * stride:(line + 1) * stride])
            for line in range(CELL)]


def _strip(random, maps, variant):
    """One raindrop, as the scanlines of a strip texture.

    The head is the bottom cell, in the colour the rain gives a cursor, and
    the brightness falls away above it. A few cells are left out along the
    way, which is what keeps a strip from looking like a printed word.
    """
    empty = [_EMPTY_ROW] * CELL
    scanlines = []
    for row in range(STRIP_ROWS):
        head = row == STRIP_ROWS - 1
        if not head and random.random() < GAPS:
            cell = empty
        else:
            share = row / float(STRIP_ROWS - 1)
            lit = MIN_LIGHT + (MAX_LIGHT - MIN_LIGHT) * share
            cell = _cell(maps[random.randrange(len(maps))],
                         raindrop.colour(lit, head, variant))
        scanlines.extend(cell)
    return scanlines


def generate(folder, variant, on_progress=None):
    """Write every missing strip of *variant* and return their paths.

    *on_progress* is called with the number of strips done and the total, so
    the caller can drive a progress display while this runs.
    """
    inside = rain.version_folder(folder, variant)
    os.makedirs(inside, exist_ok=True)
    strips = strip_paths(folder, variant)
    _drop_stale(inside, strips)

    missing = [path for path in strips if not os.path.exists(path)]
    if not missing:
        return strips

    maps = glyphs.load(variant.atlas, CELL, CELL, variant.glyph_edge_crop)
    done = 0
    for index, path in enumerate(strips):
        if path not in missing:
            continue
        # Seeded per strip, so an interrupted run resumes with the strips it
        # would have written the first time.
        scanlines = _strip(Random(_SEED + index), maps, variant)
        partial = path + ".part"
        write_rgba(partial, CELL, STRIP_ROWS * CELL, scanlines)
        os.replace(partial, path)
        done += 1
        if on_progress:
            on_progress(done, len(missing))

    return strips
