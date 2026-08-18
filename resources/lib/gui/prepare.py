"""The "prepare textures" action from the settings.

A variant builds its textures the first time it is shown, which is a wait on
slow hardware. This does every switched-on variant in one go, with a progress
dialog to watch, and takes the switched-off ones back out of the cache.
"""

import xbmcgui

from core import logger
from core.addon import translate
from gui.rain import churn_sets, enabled_versions, texture_folder
from render import rain


class _Cancelled(Exception):
    """Raised out of the progress callback when the user presses cancel."""


def prepare_textures():
    """Build the textures of every switched-on variant, showing progress."""
    variants = enabled_versions()
    folder = texture_folder()
    dialog = xbmcgui.DialogProgress()
    dialog.create(translate(32000), translate(32098))

    try:
        for number, variant in enumerate(variants):
            def report(done, total, number=number):
                if dialog.iscanceled():
                    raise _Cancelled
                share = (number + float(done) / total) / len(variants)
                dialog.update(int(share * 100), "{} ({}/{})".format(
                    translate(32098), number + 1, len(variants)))

            report(0, 1)
            rain.generate(folder, variant, report, churn_sets())
    except _Cancelled:
        logger.info("Preparing the textures was cancelled")
    except OSError as exc:
        logger.error("Could not prepare the textures: {}".format(exc))
        dialog.close()
        xbmcgui.Dialog().ok(translate(32000), translate(32082))
        return
    finally:
        dialog.close()

    dropped = rain.drop_folders(folder, set(one.name for one in variants))
    if dropped:
        logger.info("Dropped the textures of {}".format(", ".join(dropped)))
