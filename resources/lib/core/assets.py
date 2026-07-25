"""The catalogue of Matrix scenes shipped with the addon.

Three files describe the same 17 scenes: ``resources/playlist/playlist.json``
holds the name and video URL, ``resources/settings.xml`` holds one toggle per
scene and ``strings.po`` holds one label per scene. They used to be linked by
lowercasing the JSON name and stripping spaces, which silently broke for every 
multi-word scene -- "3D Alternative" produced ``enable-3dalternative`` while the 
setting is called ``enable-3d-alt``, so those scenes could never be switched off.
The three sides are mapped explicitly here instead.
"""

import os
from collections import namedtuple

from core.addon import ADDON_PATH

#: Local copy of the video list that ships with the addon
PLAYLIST_PATH = os.path.join(ADDON_PATH, "resources", "playlist", "playlist.json")

#: Keys that may hold a playable URL inside an asset block, best quality first
VIDEO_KEYS = ("video",)

#: name       -- the "name" field in playlist.json
#: setting_id -- the toggle in settings.xml
#: label_id   -- the short label in strings.po, used by the download picker
MatrixAsset = namedtuple("MatrixAsset", ("name", "setting_id", "label_id"))

ASSETS = (
    MatrixAsset("3D", "enable-3d", 32058),
    MatrixAsset("3D Alternative", "enable-3d-alt", 32059),
    MatrixAsset("Black and White", "enable-black-white", 32060),
    MatrixAsset("Bugs", "enable-bugs", 32061),
    MatrixAsset("Classic", "enable-classic", 32062),
    MatrixAsset("Classic Intro", "enable-classic-intro", 32063),
    MatrixAsset("Debug", "enable-debug", 32064),
    MatrixAsset("Megacity", "enable-megacity", 32065),
    MatrixAsset("Morpheus", "enable-morpheus", 32066),
    MatrixAsset("Nightmare", "enable-nightmare", 32067),
    MatrixAsset("Operator", "enable-operator", 32068),
    MatrixAsset("Palimpsest", "enable-palimpsest", 32069),
    MatrixAsset("Paradise", "enable-paradise", 32070),
    MatrixAsset("Rainbow", "enable-rainbow", 32071),
    MatrixAsset("Resurrections", "enable-resurrections", 32072),
    MatrixAsset("Trinity", "enable-trinity", 32073),
    MatrixAsset("Twilight", "enable-twilight", 32074),
)

ASSETS_BY_NAME = {asset.name: asset for asset in ASSETS}


def video_url(block):
    """Return the first non-empty video URL in an asset block, or ``None``."""
    for key in VIDEO_KEYS:
        url = block.get(key)
        if url:
            return url
    return None


def file_name_for(url):
    """The bare file name a video URL is stored under on disk."""
    return url.split("/")[-1].split("?")[0]
