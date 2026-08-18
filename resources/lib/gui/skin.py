"""Names and control ids of the window definitions in resources/skins/default."""

import xbmc

from core.addon import ADDON_PATH

SCREENSAVER_XML = "screensaver-matrix.xml"
TRANSPARENT_XML = "screensaver-matrix-trans.xml"
RAIN_XML = "screensaver-matrix-rain.xml"

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


def show_modal(window_class, xml_file, configure=None):
    """Open *window_class* modally and drop the reference once it closes.

    *configure* is called with the window before it opens, which is how the
    caller hands over anything the window needs -- Kodi builds the instance
    itself, so its constructor cannot take arguments of ours.
    """
    window = window_class(xml_file, ADDON_PATH, FOLDER, RESOLUTION)
    if configure is not None:
        configure(window)
    try:
        window.doModal()
    finally:
        xbmc.sleep(100)
        del window
