"""Generates the column textures the live code rain is built from.

One texture is one column of falling glyphs. It holds two identical copies of
the same pattern stacked on top of each other, so a control that is twice the
screen height and slides down by exactly one screen height loops without a
visible seam. Everything the animation needs -- the glyphs, the fading trails,
the bright heads -- is baked into the texture, which leaves the animation
itself to the skin engine and costs nothing per frame.

Nothing in here talks to Kodi, so the textures can be generated and inspected
outside of it as well.
"""

import os
from random import Random

from render import glyphs
from render.png import write_rgba

#: Design resolution the textures are drawn for. The window scales them to
#: whatever coordinate system Kodi hands out, so these never change.
DESIGN_HEIGHT = 1080

#: Edge length of one glyph cell in the design resolution
CELL = 40

#: Cells per screen height; also the period the pattern repeats with
ROWS = DESIGN_HEIGHT // CELL

#: The texture is two periods tall so it can scroll seamlessly
STRIP_HEIGHT = ROWS * 2 * CELL

#: Number of different columns generated. Enough for every column of an
#: ultra-wide screen to get its own texture, because two columns sharing one
#: would scroll the same glyphs at the same time and give the trick away.
STRIP_COUNT = 64

#: Brightness steps of a trail, from the faintest tail to the head
LEVELS = 16

#: Colour of the trail and of the leading glyph
TRAIL_COLOUR = (0, 255, 70)
HEAD_COLOUR = (205, 255, 220)

#: Where the trail starts turning white towards the head
_WHITEN_FROM = 0.72

#: Chance that an otherwise empty cell holds a barely visible glyph
BACKGROUND_CHANCE = 0.05

#: Trails per column and period, and how long they may be, in cells
DROPS_PER_PERIOD = (1, 1, 1, 2)
MIN_TRAIL, MAX_TRAIL = 5, 14

#: Raised whenever the shape of the textures changes, so old files in the
#: cache folder are not mistaken for current ones.
CACHE_VERSION = 1

#: Fixed seed: the textures are cached on disk, and a stable seed means the
#: same addon version always produces the same files.
_SEED = 0x4D4154


def _level_colour(level):
    """Colour and alpha of one brightness step, ``LEVELS - 1`` being the head."""
    position = level / float(LEVELS - 1)
    if level == LEVELS - 1:
        return HEAD_COLOUR, 255
    whiten = max(0.0, (position - _WHITEN_FROM) / (1.0 - _WHITEN_FROM)) ** 2
    colour = tuple(
        int(round(trail + (head - trail) * whiten))
        for trail, head in zip(TRAIL_COLOUR, HEAD_COLOUR))
    return colour, max(12, int(round(255 * position ** 1.7)))


def _cell_rows(coverage, colour, alpha):
    """One glyph in one brightness step, as ``CELL`` rows of RGBA bytes.

    The glyph colour is written to every pixel and only the alpha channel
    follows the coverage map. Fully transparent pixels therefore still carry
    the right colour, so scaling the texture cannot draw a dark seam around
    the strokes.
    """
    red, green, blue = colour
    pixels = len(coverage)
    scale = bytes((value * alpha) // 255 for value in range(256))

    buffer = bytearray(pixels * 4)
    buffer[0::4] = bytes((red,)) * pixels
    buffer[1::4] = bytes((green,)) * pixels
    buffer[2::4] = bytes((blue,)) * pixels
    buffer[3::4] = coverage.translate(scale)

    stride = CELL * 4
    return [bytes(buffer[index * stride:(index + 1) * stride])
            for index in range(CELL)]


def _column_pattern(random, glyph_count):
    """One period of a column as ``(glyph, level)`` per cell, ``None`` if empty."""
    cells = [None] * ROWS

    for index in range(ROWS):
        if random.random() < BACKGROUND_CHANCE:
            cells[index] = (random.randrange(glyph_count), 0)

    for _ in range(random.choice(DROPS_PER_PERIOD)):
        length = random.randint(MIN_TRAIL, MAX_TRAIL)
        head = random.randrange(ROWS)
        for distance in range(length):
            # The head is the lowest glyph, the trail hangs above it and wraps
            # around the period the same way the texture does.
            index = (head - distance) % ROWS
            level = int(round((1.0 - distance / float(length)) * (LEVELS - 1)))
            current = cells[index]
            if current is None:
                cells[index] = (random.randrange(glyph_count), level)
            elif level > current[1]:
                cells[index] = (current[0], level)

    return cells


class _CellCache:
    """Builds each glyph and brightness step once and hands out its rows."""

    def __init__(self, coverage_maps):
        self.coverage_maps = coverage_maps
        self.empty = [bytes(CELL * 4)] * CELL
        self.rows = {}

    def get(self, cell):
        if cell is None:
            return self.empty
        rows = self.rows.get(cell)
        if rows is None:
            glyph, level = cell
            colour, alpha = _level_colour(level)
            rows = _cell_rows(self.coverage_maps[glyph], colour, alpha)
            self.rows[cell] = rows
        return rows


def strip_file_name(index):
    """Name the texture of column *index* is cached under."""
    return "rain-v{}-{}-{}-{:02d}.png".format(CACHE_VERSION, CELL, LEVELS, index)


def strip_paths(folder):
    """Where all column textures live, whether they exist yet or not."""
    return [os.path.join(folder, strip_file_name(index))
            for index in range(STRIP_COUNT)]


def generate(folder, on_progress=None):
    """Write every missing column texture into *folder* and return their paths.

    *on_progress* is called with the number of textures done and the total,
    so the caller can drive a progress display while this runs.
    """
    os.makedirs(folder, exist_ok=True)
    paths = strip_paths(folder)
    missing = [(index, path) for index, path in enumerate(paths)
               if not os.path.exists(path)]
    if not missing:
        return paths

    cells = _CellCache(glyphs.rasterise(CELL))
    total = len(missing)
    for done, (index, path) in enumerate(missing, start=1):
        # Seeded per column, so an interrupted run resumes with the same
        # textures it would have written the first time.
        pattern = _column_pattern(Random(_SEED + index), glyphs.GLYPH_COUNT)
        scanlines = []
        for _ in range(2):
            for cell in pattern:
                scanlines.extend(cells.get(cell))

        # Write next to the target and rename, so a run that is cut short
        # cannot leave a half-written texture behind that later looks cached.
        partial = path + ".part"
        write_rgba(partial, CELL, STRIP_HEIGHT, scanlines)
        os.replace(partial, path)

        if on_progress:
            on_progress(done, total)

    return paths
