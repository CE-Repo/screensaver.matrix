"""Minimal PNG writer for the generated rain textures.

Kodi ships no imaging library, so the textures are encoded here. Only what the
rain needs is implemented: 8 bit RGBA, no interlacing, no palette.
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
