"""Single point of contact with the Kodi addon API.

Settings, dialogs and translations are read through the helpers below so the
rest of the addon never has to deal with the differences between Kodi releases.
"""

import os

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


#: Window the lock flag is kept on. Home is always there, its properties are
#: shared by every Python interpreter Kodi runs, and they are gone after a
#: restart -- so a crash can never leave the flag stuck.
_HOME_WINDOW = 10000
_LOCK_PROPERTY = "{}.locked".format(ADDON_ID)


def _settings():
    """Kodi 20's settings object, or None on releases that predate it."""
    try:
        return ADDON.getSettings()
    except AttributeError:
        return None


def get_bool(setting_id, default=False):
    """Read a boolean setting.

    Kodi's behaviour for ids that are not declared in settings.xml differs
    between releases -- some raise, others return the wrong type -- so an
    unreadable setting falls back to *default* instead of breaking the scene.
    """
    try:
        settings = _settings()
        if settings is not None:
            return bool(settings.getBool(setting_id))
        return bool(ADDON.getSettingBool(setting_id))
    except Exception as exc:
        logger.debug("Setting '{}' is not readable as bool ({}), using {}".format(
            setting_id, exc, default))
        return default


def get_int(setting_id, default=0):
    """Read an integer setting, falling back to *default* if it is unknown."""
    try:
        settings = _settings()
        if settings is not None:
            return int(settings.getInt(setting_id))
        return int(ADDON.getSettingInt(setting_id))
    except Exception as exc:
        logger.debug("Setting '{}' is not readable as int ({}), using {}".format(
            setting_id, exc, default))
        return default


def is_locked():
    """Whether our own window is up, so the screensaver must not start over."""
    return xbmcgui.Window(_HOME_WINDOW).getProperty(_LOCK_PROPERTY) == "true"


def set_locked(locked):
    """Mark our own window as up or gone."""
    window = xbmcgui.Window(_HOME_WINDOW)
    if locked:
        window.setProperty(_LOCK_PROPERTY, "true")
    else:
        window.clearProperty(_LOCK_PROPERTY)


def profile_folder():
    """The addon's own data folder as a real filesystem path.

    Kodi reports it as a ``special://`` path, which ``os.path`` cannot join
    correctly, so it is translated before anything builds file paths from it.
    """
    return xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))


def read_state(name, default=""):
    """Read a small value the addon keeps for itself in its profile folder.

    Kept out of the settings on purpose: writing a setting rewrites the whole
    settings file and wakes every settings listener, which is a lot of wear on
    the SD card of a Raspberry Pi for a value nobody ever edits.
    """
    try:
        with open(os.path.join(profile_folder(), name), encoding="utf-8") as handle:
            return handle.read().strip() or default
    except OSError:
        return default


def write_state(name, value):
    """Write a value for :func:`read_state`, logging instead of raising."""
    folder = profile_folder()
    try:
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, name), "w", encoding="utf-8") as handle:
            handle.write(value)
    except OSError as exc:
        logger.error("Could not write '{}': {}".format(name, exc))


def notification(header, message, display_time=2000, icon=None, sound=True):
    """Show a toast in the corner of the screen."""
    xbmcgui.Dialog().notification(header, message, icon or ADDON_ICON, display_time, sound)
