"""Names and control ids of the window definitions in resources/skins/default."""

import os

import xbmc

from core.addon import ADDON_PATH

SCREENSAVER_XML = "screensaver-matrix.xml"
TRANSPARENT_XML = "screensaver-matrix-trans.xml"
RAIN_XML = "screensaver-matrix-rain.xml"

#: The plain black texture of the skin, addressed by path because a control
#: built in Python is not resolved against the skin's own media folder.
BLACK_TEXTURE = os.path.join(
    ADDON_PATH, "resources", "skins", "default", "media", "black.jpg")

#: Skin folder below resources/skins; the empty resolution lets Kodi pick
#: between the 1080i and 720p variants itself.
FOLDER = "default"
RESOLUTION = ""

#: Control ids defined in screensaver-matrix.xml
STATUS_LABEL = 32502
MESSAGE_LABEL = 32503

#: Window property the skin watches to hide the loading screen. The skin tests
#: for the literal string "false", so any other value keeps the overlay up.
LOADING_PROPERTY = "screensaver-matrix-loading"
LOADING_ON = "true"
LOADING_OFF = "false"


def show_modal(window_class, xml_file):
    """Open *window_class* modally and drop the reference once it closes."""
    window = window_class(xml_file, ADDON_PATH, FOLDER, RESOLUTION)
    try:
        window.doModal()
    finally:
        xbmc.sleep(100)
        del window
