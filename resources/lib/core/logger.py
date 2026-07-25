"""Prefixed logging, so every line this addon writes is easy to find in kodi.log."""

import xbmc

PREFIX = "[Matrix Screensaver]"


def _log(message, level):
    xbmc.log("{} {}".format(PREFIX, message), level=level)


def debug(message):
    _log(message, xbmc.LOGDEBUG)


def info(message):
    _log(message, xbmc.LOGINFO)


def warning(message):
    _log(message, xbmc.LOGWARNING)


def error(message):
    _log(message, xbmc.LOGERROR)
