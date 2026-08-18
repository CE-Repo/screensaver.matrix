"""The glyph set of the code rain, drawn from stroke data.

The Matrix uses mirrored katakana in a font that cannot be shipped here, and
Kodi resolves fonts against the active skin, so a text control could not
display those characters reliably either. The glyphs below are therefore
described as line segments on a unit square and rasterised into small coverage
maps, which the rain assembles into its column textures.
"""

#: Grid the strokes are placed on: left/centre/right and top/middle/bottom,
#: plus the two quarter positions in between.
_L, _C, _R = 0.16, 0.50, 0.84
_T, _M, _B = 0.14, 0.50, 0.86
_Q, _S = 0.32, 0.68

#: One entry per glyph, each a tuple of (x0, y0, x1, y1) strokes. The shapes
#: are katakana-like rather than actual characters -- at column width they read
#: as the same alphabet without needing a font.
_BASE_STROKES = (
    ((_L, _T, _R, _T), (_R, _T, _R, _Q), (_L, _M, _R, _M), (_C, _M, _L, _B)),
    ((_L, _Q, _R, _Q), (_S, _T, _S, _M), (_S, _M, _L, _B), (_S, _M, _R, _B)),
    ((_L, _B, _C, _T), (_C, _Q, _C, _B)),
    ((_Q, _T, _S, _T), (_L, _Q, _R, _Q), (_R, _Q, _R, _M), (_R, _M, _C, _B)),
    ((_L, _T, _R, _T), (_C, _T, _C, _B), (_L, _B, _R, _B)),
    ((_Q, _T, _S, _T), (_L, _Q, _R, _Q), (_S, _Q, _Q, _B), (_C, _M, _R, _B)),
    ((_L, _Q, _R, _Q), (_S, _T, _S, _M), (_S, _M, _L, _B), (_L, _M, _L, _S)),
    ((_L, _Q, _R, _Q), (_L, _M, _R, _M), (_S, _T, _Q, _B)),
    ((_L, _T, _R, _T), (_R, _T, _C, _M), (_C, _M, _L, _B), (_C, _M, _R, _B)),
    ((_Q, _T, _Q, _M), (_Q, _M, _R, _M), (_R, _T, _L, _B)),
    ((_L, _T, _R, _T), (_R, _T, _R, _B), (_L, _B, _R, _B)),
    ((_L, _Q, _R, _Q), (_Q, _T, _Q, _M), (_S, _T, _S, _M), (_C, _M, _C, _B)),
    ((_L, _T, _Q, _Q), (_L, _M, _Q, _S), (_R, _T, _C, _B)),
    ((_L, _T, _R, _T), (_R, _T, _L, _B), (_C, _M, _R, _B)),
    ((_L, _T, _L, _M), (_L, _M, _R, _M), (_C, _T, _C, _B), (_R, _M, _R, _S)),
    ((_L, _T, _Q, _Q), (_R, _T, _C, _B)),
    ((_L, _T, _R, _T), (_R, _T, _C, _B), (_L, _M, _C, _M)),
    ((_Q, _T, _S, _Q), (_L, _Q, _R, _Q), (_C, _Q, _C, _B)),
    ((_L, _T, _Q, _Q), (_C, _T, _C, _Q), (_R, _T, _C, _B)),
    ((_Q, _T, _S, _T), (_L, _M, _R, _M), (_C, _M, _C, _B)),
    ((_C, _T, _C, _B), (_C, _Q, _R, _M)),
    ((_L, _Q, _R, _Q), (_S, _T, _S, _B), (_L, _M, _C, _B)),
    ((_Q, _T, _S, _T), (_L, _B, _R, _B)),
    ((_L, _Q, _R, _Q), (_R, _Q, _L, _B), (_C, _S, _R, _B)),
    ((_C, _T, _C, _Q), (_L, _Q, _R, _Q), (_C, _Q, _L, _B), (_C, _M, _R, _B)),
    ((_Q, _T, _L, _B), (_S, _T, _R, _B)),
    ((_L, _T, _L, _S), (_L, _S, _R, _M), (_L, _S, _R, _B)),
    ((_L, _T, _R, _T), (_R, _T, _C, _B)),
    ((_C, _T, _L, _M), (_L, _M, _R, _S), (_Q, _M, _R, _T)),
    ((_L, _T, _R, _T), (_L, _T, _L, _B), (_L, _B, _R, _B), (_R, _T, _R, _B)),
    ((_C, _T, _C, _B), (_Q, _Q, _C, _T)),
    ((_L, _T, _R, _T), (_R, _T, _Q, _B)),
    ((_L, _T, _R, _T), (_R, _T, _L, _B), (_L, _B, _R, _B)),
    ((_L, _M, _R, _M),),
)


def _mirrored(strokes):
    """The same shape flipped horizontally, the way the film's glyphs are."""
    return tuple((1.0 - x0, y0, 1.0 - x1, y1) for x0, y0, x1, y1 in strokes)


#: Base shapes and their mirror images, which doubles the alphabet for free.
GLYPH_STROKES = _BASE_STROKES + tuple(
    _mirrored(strokes) for strokes in _BASE_STROKES)

GLYPH_COUNT = len(GLYPH_STROKES)

#: Samples per pixel and axis while rasterising; the coverage maps are
#: downsampled afterwards, which is what gives the strokes smooth edges.
_SUPERSAMPLE = 3

#: Stroke half-width and margin around the glyph, both as a share of the cell.
_STROKE_RADIUS = 0.042
_MARGIN = 0.10


def _draw_stroke(coverage, size, x0, y0, x1, y1, radius):
    """Mark every sample within *radius* of the segment as covered."""
    delta_x, delta_y = x1 - x0, y1 - y0
    length_sq = delta_x * delta_x + delta_y * delta_y
    radius_sq = radius * radius

    first_x = max(0, int(min(x0, x1) - radius))
    last_x = min(size - 1, int(max(x0, x1) + radius) + 1)
    first_y = max(0, int(min(y0, y1) - radius))
    last_y = min(size - 1, int(max(y0, y1) + radius) + 1)

    for pixel_y in range(first_y, last_y + 1):
        row = pixel_y * size
        sample_y = pixel_y + 0.5
        for pixel_x in range(first_x, last_x + 1):
            sample_x = pixel_x + 0.5
            if length_sq:
                along = ((sample_x - x0) * delta_x + (sample_y - y0) * delta_y) / length_sq
                along = 0.0 if along < 0.0 else (1.0 if along > 1.0 else along)
            else:
                along = 0.0
            gap_x = sample_x - (x0 + along * delta_x)
            gap_y = sample_y - (y0 + along * delta_y)
            if gap_x * gap_x + gap_y * gap_y <= radius_sq:
                coverage[row + pixel_x] = 255


def _downsample(samples, sampled_size, cell):
    """Average each block of samples into one coverage byte."""
    coverage = bytearray(cell * cell)
    divisor = _SUPERSAMPLE * _SUPERSAMPLE
    for out_y in range(cell):
        top = out_y * _SUPERSAMPLE * sampled_size
        out_row = out_y * cell
        for out_x in range(cell):
            left = out_x * _SUPERSAMPLE
            total = 0
            for offset in range(_SUPERSAMPLE):
                start = top + offset * sampled_size + left
                total += sum(samples[start:start + _SUPERSAMPLE])
            coverage[out_row + out_x] = total // divisor
    return coverage


def rasterise(cell):
    """Coverage maps of every glyph, each ``cell * cell`` bytes, 0 to 255."""
    sampled_size = cell * _SUPERSAMPLE
    radius = max(1.0, sampled_size * _STROKE_RADIUS)
    inset = sampled_size * _MARGIN
    span = sampled_size - 2 * inset

    maps = []
    for strokes in GLYPH_STROKES:
        samples = bytearray(sampled_size * sampled_size)
        for x0, y0, x1, y1 in strokes:
            _draw_stroke(samples, sampled_size,
                         inset + x0 * span, inset + y0 * span,
                         inset + x1 * span, inset + y1 * span, radius)
        maps.append(_downsample(samples, sampled_size, cell))
    return maps
