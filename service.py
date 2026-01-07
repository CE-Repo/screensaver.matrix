from resources.lib.common import addon

# set locked setting back to false on startup just in case kodi had crashed during playback
addon.setSettingBool("is_locked", False)
