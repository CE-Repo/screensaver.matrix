# Glyph atlases

These files are the glyph sets the live code rain draws with, taken unchanged
from [Rezmason/matrix](https://github.com/Rezmason/matrix) (its `assets/`
folder), where they are generated from SVG sources with
[msdfgen](https://github.com/Chlumsky/msdfgen).

| File | Grid | Used by |
| --- | --- | --- |
| `matrixcode_msdf.png` | 8x8 | Classic, Operator, Rainbow |
| `megacity_msdf.png` | 8x8 | Megacity |
| `gothic_msdf.png` | 8x8 | Nightmare |
| `coptic_msdf.png` | 8x8 | Paradise |
| `resurrections_msdf.png` | 13x12 | Resurrections |
| `huberfish_a_msdf.png` | 6x6 | Palimpsest |
| `huberfish_d_msdf.png` | 6x6 | Twilight |

Each is a multi-channel signed distance field: a grid of 64x64 cells, one glyph
per cell, with the empty cells at the end. A distance field is not a picture of
the glyphs -- the three colour channels encode how far each pixel is from the
nearest edge, which is what lets `resources/lib/render/glyphs.py` cut clean
outlines out of them at whatever size the rain needs.

The files are MIT licensed; the licence text sits next to them in
`LICENSE.Rezmason.txt` and has to stay with them.
