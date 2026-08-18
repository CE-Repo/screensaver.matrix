# Glyph atlas

`matrixcode_msdf.png` is the glyph atlas of the films' code, taken unchanged
from [Rezmason/matrix](https://github.com/Rezmason/matrix)
(`assets/matrixcode_msdf.png`), where it is generated from SVG sources with
[msdfgen](https://github.com/Chlumsky/msdfgen).

It is a 512x512 multi-channel signed distance field: an 8x8 grid of 64x64
cells, 57 of which carry a glyph. A distance field is not a picture of the
glyphs -- the three colour channels encode how far each pixel is from the
nearest edge, which is what lets `resources/lib/render/glyphs.py` cut clean
outlines out of it at whatever size the rain needs.

The file is MIT licensed; the licence text sits next to it in
`LICENSE.Rezmason.txt` and has to stay with the file.
