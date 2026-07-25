"""Turns the bundled video catalogue into the list the screensaver plays."""

import json
import os
from random import shuffle

import xbmcvfs

from core import logger
from core.addon import download_folder, get_bool
from core.assets import ASSETS_BY_NAME, PLAYLIST_PATH, file_name_for, video_url


def load_catalogue():
    """Read the bundled playlist.json, returning ``{}`` when it is unusable."""
    try:
        with open(PLAYLIST_PATH, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError) as exc:
        logger.error("Could not read {}: {}".format(PLAYLIST_PATH, exc))
        return {}


class MatrixPlaylist:
    """The scenes from playlist.json, filtered by the user's settings."""

    def __init__(self):
        self.catalogue = load_catalogue()

    def assets(self):
        """All scene blocks in the catalogue, in file order."""
        return self.catalogue.get("assets", [])

    def build(self):
        """The shuffled list of URLs or local paths to play, possibly empty."""
        force_offline = get_bool("force-offline")
        folder = download_folder() if force_offline else ""
        if force_offline and not folder:
            logger.warning("Offline mode is on but no download folder is set")

        playlist = []
        for block in self.assets():
            name = block.get("name", "")
            asset = ASSETS_BY_NAME.get(name)
            if asset is None:
                # A scene added to playlist.json but not yet to settings.xml
                # stays in the rotation rather than disappearing silently.
                logger.debug("Scene '{}' has no setting, keeping it enabled".format(name))
            elif not get_bool(asset.setting_id, default=True):
                continue

            url = video_url(block)
            if not url:
                logger.debug("Scene '{}' has no video URL, skipping".format(name))
                continue

            if force_offline:
                # Offline mode never touches the network: either the downloaded
                # copy is played or the scene drops out of the rotation.
                local_path = os.path.join(folder, file_name_for(url))
                if not xbmcvfs.exists(local_path):
                    logger.debug("No local copy of '{}', skipping".format(name))
                    continue
                url = local_path

            playlist.append(url)

        shuffle(playlist)
        return playlist
