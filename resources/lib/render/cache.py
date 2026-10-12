"""What the rain and the tunnel share about keeping textures on disk."""

import os

from render.png import write_rgba


class Cancelled(Exception):
    """Raised out of a progress callback to stop generating textures."""


def drop_stale(folder, current, prefixes):
    """Delete textures an earlier version of the addon left behind.

    Only names starting with one of *prefixes* are considered, so whatever
    else lives in the folder is left alone.
    """
    keep = set(os.path.basename(path) for path in current)
    for name in os.listdir(folder):
        if name.startswith(prefixes) and name not in keep:
            try:
                os.remove(os.path.join(folder, name))
            except OSError:
                # A leftover we cannot delete costs disk space and nothing
                # else, so it must not stop the scene from starting.
                pass


def write(path, width, height, scanlines):
    """Write a texture, but only move it into place once it is complete."""
    partial = path + ".part"
    write_rgba(partial, width, height, scanlines)
    os.replace(partial, path)
