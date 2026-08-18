"""The glyph set of the code rain, cut from the films' own glyph atlas.

``resources/glyphs/matrixcode_msdf.png`` comes from Rezmason's Matrix project
and is a multi-channel signed distance field rather than a picture: the three
colour channels encode how far each pixel sits from the nearest glyph edge.
Reading it back is a matter of finding where that distance crosses zero, which
is what the two passes below do -- one turns the field into a coverage map with
smooth edges, the other halves it to the size the rain draws its glyphs at.

Both passes work on whole byte strings instead of single pixels: the per-pixel
comparisons are expressed as ``bytes.translate`` tables and the sums as one big
integer addition each, so the entire atlas is converted in a few milliseconds
even without an imaging library.
"""

import os

from render import png

#: The atlas as shipped: 512x512, an 8x8 grid of 64x64 cells
ATLAS_SIZE = 512
ATLAS_GRID = 8
ATLAS_CELL = ATLAS_SIZE // ATLAS_GRID

#: Distance range msdfgen was run with, in atlas pixels (see the README next
#: to the atlas). A pixel value of 0.5 sits exactly on the edge of a glyph,
#: and the full 0 to 1 range spans this many pixels around it.
PIXEL_RANGE = 4

#: Edge length of a glyph in the coverage maps this module hands out. It is
#: close to the size the rain draws its glyphs at, and small enough to keep the
#: column textures below the 2048 pixel texture limit of older graphics
#: hardware. The atlas is halved first, which is quick, and resampled to this
#: size afterwards.
CELL = 22

#: Steps the edge is resolved into. Each step is one threshold through the
#: distance field, and the coverage of a pixel is how many of them it passes.
EDGE_STEPS = 16

_RESOURCES = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ATLAS_PATH = os.path.join(_RESOURCES, "glyphs", "matrixcode_msdf.png")


def _table(test):
    """A translation table mapping every byte to 1 or 0, by *test*."""
    return bytes(1 if test(value) else 0 for value in range(256))


#: The median of the three channels decides: a pixel is inside a glyph when at
#: least two of them are above the threshold.
_MAJORITY = _table(lambda votes: votes >= 2)


def _edge_thresholds():
    """The byte values the distance field is sampled at across one edge.

    Coverage runs from nothing to full over a distance of one pixel, which is
    ``1 / PIXEL_RANGE`` of the value range on either side of the edge at 0.5.
    """
    half_band = 255.0 / (2 * PIXEL_RANGE)
    step = 2 * half_band / EDGE_STEPS
    return [127.5 - half_band + (index + 0.5) * step for index in range(EDGE_STEPS)]


def _coverage(scanlines, pixels, bytes_per_pixel):
    """Turn the distance field into one coverage byte per pixel."""
    flat = b"".join(scanlines)
    channels = [flat[offset::bytes_per_pixel] for offset in range(3)]

    total = 0
    for threshold in _edge_thresholds():
        above = _table(lambda value, edge=threshold: value >= edge)
        votes = sum(int.from_bytes(channel.translate(above), "big")
                    for channel in channels)
        # Byte-wise throughout: no sum can reach 256, so nothing carries into
        # the neighbouring pixel.
        total += int.from_bytes(
            votes.to_bytes(pixels, "big").translate(_MAJORITY), "big")

    return total.to_bytes(pixels, "big").translate(
        bytes(min(255, round(255.0 * value / EDGE_STEPS)) for value in range(256)))


def _halve(coverage, width, height):
    """Average every 2x2 block into one pixel."""
    # Quartering first keeps the sum of four pixels inside one byte. The two
    # bits that costs are given back by the rescale at the end.
    quarter = bytes(value // 4 for value in range(256))
    regain = bytes(min(255, value * 255 // (4 * (255 // 4))) for value in range(256))

    halved_width = width // 2
    rows = []
    for row in range(height // 2):
        top = coverage[(2 * row) * width:(2 * row + 1) * width]
        bottom = coverage[(2 * row + 1) * width:(2 * row + 2) * width]
        total = 0
        for part in (top[0::2], top[1::2], bottom[0::2], bottom[1::2]):
            total += int.from_bytes(part.translate(quarter), "big")
        rows.append(total.to_bytes(halved_width, "big").translate(regain))
    return b"".join(rows), halved_width


def _axis_weights(source, target):
    """For every target pixel, which source pixels feed it and by how much."""
    scale = source / float(target)
    weights = []
    for index in range(target):
        start, end = index * scale, (index + 1) * scale
        first = int(start)
        last = min(int(end - 1e-9), source - 1)
        weights.append([(position,
                         (min(end, position + 1) - max(start, position)) / scale)
                        for position in range(first, last + 1)])
    return weights


def _resample(coverage, width, height, target_width, target_height):
    """Scale a coverage map by averaging over the area each pixel covers."""
    horizontal = _axis_weights(width, target_width)
    vertical = _axis_weights(height, target_height)

    stretched = []
    for row in range(height):
        line = coverage[row * width:(row + 1) * width]
        stretched.append([sum(line[position] * weight for position, weight in entries)
                          for entries in horizontal])

    resampled = bytearray(target_width * target_height)
    for row, entries in enumerate(vertical):
        offset = row * target_width
        for column in range(target_width):
            resampled[offset + column] = min(255, int(
                sum(stretched[position][column] * weight
                    for position, weight in entries)))
    return bytes(resampled)


def _cut_cells(coverage, width):
    """Split the grid into glyphs, skipping the cells that carry none."""
    glyphs = []
    for index in range(ATLAS_GRID * ATLAS_GRID):
        column, row = index % ATLAS_GRID, index // ATLAS_GRID
        block = bytearray()
        for line in range(CELL):
            start = (row * CELL + line) * width + column * CELL
            block += coverage[start:start + CELL]
        if any(block):
            glyphs.append(bytes(block))
    return glyphs


def load(path=None):
    """Coverage maps of every glyph, each ``CELL * CELL`` bytes, 0 to 255."""
    width, height, bytes_per_pixel, scanlines = png.read(path or ATLAS_PATH)
    if (width, height) != (ATLAS_SIZE, ATLAS_SIZE):
        raise ValueError("Glyph atlas is {}x{}, expected {}x{}".format(
            width, height, ATLAS_SIZE, ATLAS_SIZE))

    coverage = _coverage(scanlines, width * height, bytes_per_pixel)
    coverage, halved = _halve(coverage, width, height)
    grid = ATLAS_GRID * CELL
    coverage = _resample(coverage, halved, halved, grid, grid)
    return _cut_cells(coverage, grid)
