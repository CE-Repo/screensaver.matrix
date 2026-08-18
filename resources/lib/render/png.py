"""Minimal PNG codec for the rain textures and the glyph atlas.

Kodi ships no imaging library, so both ends are implemented here. Only what
the rain needs is covered: 8 bit RGB or RGBA, no interlacing, no palette.
"""

import struct
import zlib

_SIGNATURE = b"\x89PNG\r\n\x1a\n"

#: Colour type 6 is RGBA, bit depth 8
_BIT_DEPTH = 8
_COLOUR_TYPE_RGBA = 6

#: Every scanline is prefixed with its filter type; the rain textures are
#: mostly transparent, so "none" already compresses well.
_FILTER_NONE = b"\x00"


def _chunk(tag, payload):
    """One length-tag-payload-checksum block of the PNG container."""
    checksum = zlib.crc32(tag + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", checksum)


def write_rgba(path, width, height, scanlines):
    """Write *scanlines* -- one bytes-like of ``width * 4`` bytes per row."""
    header = struct.pack(
        ">IIBBBBB", width, height, _BIT_DEPTH, _COLOUR_TYPE_RGBA, 0, 0, 0)
    raw = b"".join(_FILTER_NONE + bytes(row) for row in scanlines)
    with open(path, "wb") as handle:
        handle.write(_SIGNATURE)
        handle.write(_chunk(b"IHDR", header))
        handle.write(_chunk(b"IDAT", zlib.compress(raw, 6)))
        handle.write(_chunk(b"IEND", b""))


def _undo_filter(line, previous, step):
    """Reverse one scanline filter in place; *line* starts with its filter byte."""
    kind = line[0]
    del line[0]
    if kind == 0:
        return
    width = len(line)
    if kind == 1:                                              # Sub
        for index in range(step, width):
            line[index] = (line[index] + line[index - step]) & 0xFF
    elif kind == 2:                                            # Up
        for index in range(width):
            line[index] = (line[index] + previous[index]) & 0xFF
    elif kind == 3:                                            # Average
        for index in range(width):
            left = line[index - step] if index >= step else 0
            line[index] = (line[index] + ((left + previous[index]) >> 1)) & 0xFF
    elif kind == 4:                                            # Paeth
        for index in range(width):
            left = line[index - step] if index >= step else 0
            above = previous[index]
            corner = previous[index - step] if index >= step else 0
            estimate = left + above - corner
            by_left = abs(estimate - left)
            by_above = abs(estimate - above)
            by_corner = abs(estimate - corner)
            if by_left <= by_above and by_left <= by_corner:
                nearest = left
            elif by_above <= by_corner:
                nearest = above
            else:
                nearest = corner
            line[index] = (line[index] + nearest) & 0xFF
    else:
        raise ValueError("Unknown PNG filter {}".format(kind))


def read(path):
    """Read a PNG and return ``(width, height, bytes_per_pixel, scanlines)``."""
    data = open(path, "rb").read()
    if not data.startswith(_SIGNATURE):
        raise ValueError("{} is not a PNG file".format(path))

    compressed = []
    width = height = bytes_per_pixel = 0
    position = len(_SIGNATURE)
    while position < len(data):
        length = struct.unpack(">I", data[position:position + 4])[0]
        tag = data[position + 4:position + 8]
        payload = data[position + 8:position + 8 + length]
        if tag == b"IHDR":
            width, height, depth, colour_type = struct.unpack(">IIBB", payload[:10])
            interlaced = payload[12]
            if depth != _BIT_DEPTH or interlaced or colour_type not in (2, _COLOUR_TYPE_RGBA):
                raise ValueError("Unsupported PNG: depth {}, colour type {}, "
                                 "interlace {}".format(depth, colour_type, interlaced))
            bytes_per_pixel = 3 if colour_type == 2 else 4
        elif tag == b"IDAT":
            compressed.append(payload)
        elif tag == b"IEND":
            break
        position += 12 + length

    raw = zlib.decompress(b"".join(compressed))
    stride = width * bytes_per_pixel
    scanlines = []
    previous = bytes(stride)
    for row in range(height):
        start = row * (stride + 1)
        line = bytearray(raw[start:start + stride + 1])
        _undo_filter(line, previous, bytes_per_pixel)
        scanlines.append(bytes(line))
        previous = line
    return width, height, bytes_per_pixel, scanlines
