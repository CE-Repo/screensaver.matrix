import xbmcaddon
import xbmcgui

addon = xbmcaddon.Addon()
addon_path = addon.getAddonInfo("path")
addon_icon = addon.getAddonInfo("icon")
dialog = xbmcgui.Dialog()


def translate(text):
    return addon.getLocalizedString(text)


def notification(header, message, time=2000, icon=addon_icon, sound=True):
    xbmcgui.Dialog().notification(header, message, icon, time, sound)


# Given a block and a set of keys to check, return the first one we find a nonempty value for
def find_ranked_key_in_dict(dict, key_list):
    for key in key_list:
        if key in dict:
            return dict[key]
    return None

