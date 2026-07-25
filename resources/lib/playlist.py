import json
import os
import tarfile
from random import shuffle
from urllib import request

import xbmc
import xbmcvfs

from .common import addon, addon_path, find_ranked_key_in_dict

# Local save location of the playlist.json file containing video URLs
local_playlist_json_path = os.path.join(addon_path, "resources", "playlist.json")

class MatrixPlaylist:
    def __init__(self):
        self.playlist = []
                # Set a class variable as the Bool response of our Setting.
        self.force_offline = addon.getSettingBool("force-offline")
        if not xbmc.getCondVisibility("Player.HasMedia"):
            xbmc.log("Use local playlist.json", level=xbmc.LOGDEBUG)
            try:
                with open(local_playlist_json_path, "r") as f:
                    self.top_level_json = json.loads(f.read())
            except Exception as e:
                xbmc.log(f"Error loading the local playlist.json: {e}", level=xbmc.LOGERROR)
                self.top_level_json = {}
        else:
            self.top_level_json = {}

    def get_playlist_json(self):
        return self.top_level_json

    def compute_playlist_array(self):
        if self.top_level_json:

            # Parse the setting to determine URL preference.
            block_key_list = ["video"]

            # Top-level JSON has assets array, initialAssetCount, version. Inspect each block in "assets"
            for block in self.top_level_json["assets"]:
                # Each block contains a location/scene whose name is stored in "name". These may recur
                # Retrieve the location name
                location = block["name"]
                try:
                    # Get the corresponding setting Bool by adding "enable-" + lowercase + no whitespace
                    current_location_enabled = addon.getSettingBool("enable-" + location.lower().replace(" ", ""))
                except TypeError:
                    xbmc.log("Location {} did not have a matching enable/disable setting".format(location),
                             level=xbmc.LOGDEBUG)
                    # Leave the location in the rotation if we couldn't find a corresponding setting disabling it
                    current_location_enabled = True

                # Skip the rest of the loop if the current block's location setting has been explicitly disabled
                if not current_location_enabled:
                    continue

                # Get the URL from the current block to download
                url = find_ranked_key_in_dict(block, block_key_list)

                # If the URL is empty/None, skip the rest of the loop
                if not url:
                    continue

                # Get just the file's name, without the HTTP URL part
                file_name = url.split("/")[-1]

                # The download folder is only consulted when the user asked for local
                # playback. With that setting off we keep the network URL, so the video
                # streams from the host instead of a copy downloaded earlier
                if self.force_offline:
                    local_file_path = os.path.join(addon.getSetting("download-folder"), file_name)
                    if not xbmcvfs.exists(local_file_path):
                        # Nothing to play for this location without a network connection
                        xbmc.log("Local file missing for location {}, skipping".format(location),
                                 level=xbmc.LOGDEBUG)
                        continue
                    url = local_file_path
                    xbmc.log("Video available locally, path is: {}".format(local_file_path), level=xbmc.LOGDEBUG)
                else:
                    xbmc.log("Streaming video for location {} from {}".format(location, url),
                             level=xbmc.LOGDEBUG)

                self.playlist.append(url)

            # Now that we're done building the playlist, shuffle and return to the caller
            shuffle(self.playlist)
            return self.playlist
        else:
            return None
