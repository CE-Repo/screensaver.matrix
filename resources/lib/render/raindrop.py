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

#: The wobble's two harmonics per texture loop, and their amplitudes. The
#: original runs them at sqrt(2) and sqrt(5) radians per cycle; over five
#: cycles those come out closest to one and two whole waves. Shorter loops
#: scale the amplitudes down with them, which keeps the wobble from ever
#: running backwards -- it never does in the original either.
WOBBLE_HARMONICS = ((1, 0.3), (2, 0.2))
WOBBLE_REFERENCE_CYCLES = 5


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


def cycle_rows(version):
    """Rows one raindrop cycle spans.

    Straight out of the shader's arithmetic: a row advances the wave by
    ``0.01 / raindropLength``, and a full cycle is 1.0.
    """
    return int(round(100 * version.raindrop_length))


def wobble(position, cycles):
    """Stretches and squeezes the wave, so no two raindrops are the same length."""
    scale = min(1.0, float(cycles) / WOBBLE_REFERENCE_CYCLES)
    total = position
    for harmonic, amplitude in WOBBLE_HARMONICS:
        total += amplitude * scale * math.sin(
            2 * math.pi * harmonic * position / cycles)
    return total


def brightness(row, column_time, version, cycles):
    """How lit the glyph in *row* is, 0 to 1. Row 0 is the bottom of the grid."""
    position = (row * 0.01 + column_time) / version.raindrop_length
    return 1.0 - _fract(wobble(position, cycles))


def palette(stops, position):
    """The colour *stops* hold at *position*, interpolated between them."""
    if position <= stops[0][0]:
        return stops[0][1]
    for (low, low_colour), (high, high_colour) in zip(stops, stops[1:]):
        if position <= high:
            share = (position - low) / (high - low)
            return tuple(int(round(start + (end - start) * share))
                         for start, end in zip(low_colour, high_colour))
    return stops[-1][1]


def colour(lit, is_cursor, version):
    """The colour of a glyph that is *lit* this much, cursor or not.

    A version with stripes has no palette of its own: its light is drawn white
    and tinted per column afterwards, which is how the stripe pass works.
    """
    base = lit * version.base_contrast + version.base_brightness
    if (version.brightness_override > 0 and not is_cursor
            and base > version.brightness_threshold):
        # Versions that do not fade their glyphs pin them to one brightness
        base = version.brightness_override
    base = min(1.0, max(0.0, base))

    if is_cursor:
        # The palette contributes nothing to a cursor; its colour is added on
        # top of it instead, and clipped per channel.
        tint = (255, 255, 255) if version.stripes else version.cursor_colour
        return tuple(min(255, int(round(channel * version.cursor_intensity * base)))
                     for channel in tint)
    if version.stripes:
        value = int(round(255 * base))
        return (value, value, value)
    return palette(version.palette, base)


def column_colours(rows, column, top_row, version, cycles):
    """The colours of one column, from *top_row* downwards, cursors included.

    Returns one ``(red, green, blue)`` per row, top to bottom, ready to be
    written into a light texture.
    """
    time_offset, _ = column_offsets(column)
    lit = [brightness(top_row - offset, time_offset, version, cycles)
           for offset in range(rows + 1)]
    # A glyph is the cursor when the one below it is darker: that is the
    # bottom end of a raindrop, where the wave has just wrapped around.
    cursor = version.isolate_cursor
    return [colour(lit[index], cursor and lit[index] > lit[index + 1], version)
            for index in range(rows)]
