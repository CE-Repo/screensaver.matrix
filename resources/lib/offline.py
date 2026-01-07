import xbmc
import xbmcvfs

from .common import dialog, addon, translate, find_ranked_key_in_dict
from .downloader import Downloader
from .playlist import MatrixPlaylist

# Original names from JSON, exactly as in playlist.json
original_names = [
    "3D",
    "3D Alternative",
    "Black and White",
    "Bugs",
    "Classic",
    "Classic Intro",
    "Debug",
    "Megacity",
    "Morpheus",
    "Nightmare",
    "Operator",
    "Palimpsest",
    "Paradise",
    "Rainbow",
    "Resurrections",
    "Trinity",
    "Twilight"
]

translation_ids = list(range(32058, 32075))
translated_names = [translate(i) for i in translation_ids]
all_str = translate(32057)
locations = [all_str] + translated_names
translation_to_original = dict(zip(translated_names, original_names))

def offline():
    # Note: Download folder must be set and exist in the settings
    if addon.getSetting("download-folder") and xbmcvfs.exists(addon.getSetting("download-folder")):
        # Dialog mit Auswahl (Überschrift und Liste)
        locations_chosen_index = dialog.select(translate(32007), locations)

        if locations_chosen_index > -1:
            top_level_json = MatrixPlaylist().get_playlist_json()
            download_list = []

            if top_level_json and "assets" in top_level_json:
                # If “All” is selected, then all original_names, otherwise only the matching one
                if locations_chosen_index == 0:
                    selected_original_names = original_names
                else:
                    selected_translated_name = locations[locations_chosen_index]
                    selected_original_name = translation_to_original.get(selected_translated_name)
                    if not selected_original_name:
                        # Fallback, if translation is missing
                        selected_original_name = selected_translated_name
                    selected_original_names = [selected_original_name]

                block_key_list = ["video"]

                for block in top_level_json["assets"]:
                    location = block.get("name", "")

                    # Download only suitable locations
                    if location not in selected_original_names:
                        xbmc.log(f"Current location '{location}' is not chosen location, skipping download", level=xbmc.LOGDEBUG)
                        continue

                    url = find_ranked_key_in_dict(block, block_key_list)

                    if url:
                        download_list.append(url)
                    else:
                        xbmc.log(f"The needed quality does not exist for current location '{location}', skipping", level=xbmc.LOGDEBUG)

            if download_list:
                Downloader().download_videos_from_urls(download_list)
            else:
                dialog.ok(translate(32000), translate(32005))
    else:
        dialog.ok(translate(32000), translate(32006))
