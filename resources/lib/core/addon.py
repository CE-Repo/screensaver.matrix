"""Single point of contact with the Kodi addon API.

Settings, dialogs and translations are read through the helpers below so the
rest of the addon never has to deal with the differences between Kodi releases.
"""

import xbmcaddon
import xbmcgui
import xbmcvfs

from core import logger

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")
ADDON_PATH = ADDON.getAddonInfo("path")
ADDON_ICON = ADDON.getAddonInfo("icon")


def translate(string_id):
    """Return the localised text for a numeric id from strings.po."""
    return ADDON.getLocalizedString(string_id)


def get_bool(setting_id, default=False):
    """Read a boolean setting.

    Kodi's behaviour for ids that are not declared in settings.xml differs
    between releases -- some raise, others return the wrong type -- so an
    unreadable setting falls back to *default* instead of breaking playback.
    """
    try:
        return bool(ADDON.getSettingBool(setting_id))
    except Exception as exc:
        logger.debug("Setting '{}' is not readable as bool ({}), using {}".format(
            setting_id, exc, default))
        return default


def get_int(setting_id, default=0):
    """Read an integer setting, falling back to *default* if it is unknown."""
    try:
        return int(ADDON.getSettingInt(setting_id))
    except Exception as exc:
        logger.debug("Setting '{}' is not readable as int ({}), using {}".format(
            setting_id, exc, default))
        return default


def get_string(setting_id, default=""):
    """Read a string setting, falling back to *default* if it is unknown."""
    try:
        return ADDON.getSetting(setting_id) or default
    except Exception as exc:
        logger.debug("Setting '{}' is not readable ({}), using '{}'".format(
            setting_id, exc, default))
        return default


def set_bool(setting_id, value):
    """Write a boolean setting, logging instead of raising when it fails."""
    try:
        ADDON.setSettingBool(setting_id, bool(value))
    except Exception as exc:
        logger.error("Could not write setting '{}': {}".format(setting_id, exc))


def download_folder():
    """The configured download folder as a real filesystem path, or ``""``.

    The setting may hold a ``special://`` path, which ``os.path`` cannot join
    correctly, so it is translated before anything builds file paths from it.
    """
    folder = get_string("download-folder")
    return xbmcvfs.translatePath(folder) if folder else ""


def notification(header, message, display_time=2000, icon=None, sound=True):
    """Show a toast in the corner of the screen."""
    xbmcgui.Dialog().notification(header, message, icon or ADDON_ICON, display_time, sound)


def ok_dialog(header, message):
    """Show a blocking dialog with a single OK button."""
    xbmcgui.Dialog().ok(header, message)


def select_dialog(header, options):
    """Show a list picker and return the chosen index, or -1 when cancelled."""
    return xbmcgui.Dialog().select(header, options)
