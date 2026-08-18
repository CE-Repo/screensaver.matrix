"""A port of the rain algorithm from Rezmason's Matrix project.

The shaders in that project describe the effect as two separate things: a grid
of glyphs that stay where they are, and a brightness that travels down through
them. ``rainPass.raindrop.frag.glsl`` computes that brightness, and
``palettePass.frag.glsl`` turns it into a colour. Both are reproduced here,
with the constants taken from the defaults in its ``js/config.js``.

The one deliberate change is the wobble. In the original its two sine waves run
at sqrt(2) and sqrt(5), which never line up again, so the pattern never repeats.
A texture has to repeat, so the two frequencies are moved onto the nearest whole
number of cycles per loop. They stay within a tenth of the originals, and the
condition that matters -- that the wobble never runs backwards -- still holds.
"""

import math

#: The speed the raindrops progress downwards
FALL_SPEED = 0.3

#: Adjusts the frequency of raindrops, and with that their length
RAINDROP_LENGTH = 0.75

#: Rows one raindrop cycle spans, straight out of the shader's arithmetic:
#: a row advances the wave by 0.01 / RAINDROP_LENGTH, a full cycle is 1.0.
CYCLE_ROWS = int(round(100 * RAINDROP_LENGTH))

#: Cycles per texture loop, and the wobble's two harmonics within that loop.
#: The original uses sqrt(2) and sqrt(5) radians per cycle; over five cycles
#: those come out closest to one and two whole waves.
CYCLES_PER_LOOP = 5
WOBBLE_HARMONICS = ((1, 0.3), (2, 0.2))

#: Contrast and brightness applied before the palette is looked up. Note that
#: the brightness is negative: a glyph only becomes visible once the raindrop
#: has passed 0.45, which is what cuts the wave into separate drops.
BASE_CONTRAST = 1.1
BASE_BRIGHTNESS = -0.5

#: The cursor is the brightest glyph at the bottom of a raindrop. It is not
#: taken from the palette but added on top of it, which is why it can be
#: brighter than any colour the palette holds.
CURSOR_INTENSITY = 2


def hsl(hue, saturation, lightness):
    """The colour helper the project's config is written in, as 0 to 255 RGB."""
    chroma = (1 - abs(2 * lightness - 1)) * saturation
    sector = (hue * 360.0) / 60.0
    second = chroma * (1 - abs(sector % 2 - 1))
    lowest = lightness - chroma / 2
    channels = {
        0: (chroma, second, 0.0), 1: (second, chroma, 0.0),
        2: (0.0, chroma, second), 3: (0.0, second, chroma),
        4: (second, 0.0, chroma), 5: (chroma, 0.0, second),
    }[int(sector) % 6]
    return tuple(max(0, min(255, int(round((value + lowest) * 255))))
                 for value in channels)


#: The palette the raindrop brightness is mapped onto, as (position, colour)
PALETTE = (
    (0.0, hsl(0.3, 0.9, 0.0)),
    (0.2, hsl(0.3, 0.9, 0.2)),
    (0.7, hsl(0.3, 0.9, 0.7)),
    (0.8, hsl(0.3, 0.9, 0.8)),
)

CURSOR_COLOUR = hsl(0.242, 1, 0.73)


def _fract(value):
    return value - math.floor(value)


def random_float(x, y):
    """The hash the shaders use to scatter their per-column values."""
    dot = x * 12.9898 + y * 78.233
    # GLSL's mod is always positive, unlike Python's math.fmod
    remainder = dot - math.pi * math.floor(dot / math.pi)
    return _fract(math.sin(remainder) * 43758.5453)


def column_offsets(column):
    """The starting point and the speed of one column, as the shader picks them."""
    time_offset = random_float(column, 0.0) * 1000.0
    speed_offset = random_float(column + 0.1, 0.0) * 0.5 + 0.5
    return time_offset, speed_offset


def wobble(position):
    """Stretches and squeezes the wave, so no two raindrops are the same length."""
    total = position
    for harmonic, amplitude in WOBBLE_HARMONICS:
        total += amplitude * math.sin(
            2 * math.pi * harmonic * position / CYCLES_PER_LOOP)
    return total


def brightness(row, column_time):
    """How lit the glyph in *row* is, 0 to 1. Row 0 is the bottom of the grid."""
    return 1.0 - _fract(wobble((row * 0.01 + column_time) / RAINDROP_LENGTH))


def palette(position):
    """The colour the palette holds at *position*, interpolated between stops."""
    if position <= PALETTE[0][0]:
        return PALETTE[0][1]
    for (low, low_colour), (high, high_colour) in zip(PALETTE, PALETTE[1:]):
        if position <= high:
            share = (position - low) / (high - low)
            return tuple(int(round(start + (end - start) * share))
                         for start, end in zip(low_colour, high_colour))
    return PALETTE[-1][1]


def colour(lit, is_cursor):
    """The colour of a glyph that is *lit* this much, cursor or not."""
    base = min(1.0, max(0.0, lit * BASE_CONTRAST + BASE_BRIGHTNESS))
    if is_cursor:
        # The palette contributes nothing to a cursor; its colour is added on
        # top of it instead, and clipped per channel.
        return tuple(min(255, int(round(channel * CURSOR_INTENSITY * base)))
                     for channel in CURSOR_COLOUR)
    return palette(base)


def column_colours(rows, column, top_row):
    """The colours of one column, from *top_row* downwards, cursors included.

    Returns one ``(red, green, blue)`` per row, top to bottom, ready to be
    written into a light texture.
    """
    time_offset, _ = column_offsets(column)
    lit = [brightness(top_row - offset, time_offset) for offset in range(rows + 1)]
    # A glyph is the cursor when the one below it is darker: that is the
    # bottom end of a raindrop, where the wave has just wrapped around.
    return [colour(lit[index], lit[index] > lit[index + 1])
            for index in range(rows)]
