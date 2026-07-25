"""The "Download Videos" dialog reachable from the addon settings."""

import xbmcvfs

from core import logger
from core.addon import download_folder, ok_dialog, select_dialog, translate
from core.assets import ASSETS, video_url
from download.downloader import Downloader
from playback.playlist import MatrixPlaylist

#: Label of the first entry in the picker, which selects every scene
ALL_LABEL_ID = 32057


def download_videos():
    """Ask which scenes to fetch and hand their URLs to the downloader."""
    folder = download_folder()
    if not folder or not xbmcvfs.exists(folder):
        ok_dialog(translate(32000), translate(32006))
        return

    # Entry 0 is "All"; the remaining entries follow the catalogue one to one,
    # so the chosen index maps straight back to a scene without having to look
    # translated labels up in reverse.
    options = [translate(ALL_LABEL_ID)] + [translate(asset.label_id) for asset in ASSETS]
    chosen = select_dialog(translate(32007), options)
    if chosen < 0:
        return

    if chosen == 0:
        wanted = {asset.name for asset in ASSETS}
    else:
        wanted = {ASSETS[chosen - 1].name}

    urls = []
    for block in MatrixPlaylist().assets():
        name = block.get("name", "")
        if name not in wanted:
            continue
        url = video_url(block)
        if url:
            urls.append(url)
        else:
            logger.debug("Scene '{}' has no video URL, skipping".format(name))

    if not urls:
        ok_dialog(translate(32000), translate(32005))
        return

    Downloader(folder).download_all(urls)
