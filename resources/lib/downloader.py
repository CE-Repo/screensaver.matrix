import json
import os
import threading
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

import xbmc
import xbmcgui
import xbmcvfs

from .common import *

class Downloader:

    def __init__(self):
        self.stop = False
        self.dp = None
        self.path = None
        self.num_threads = 8

    def download_videos_from_urls(self, urllist):
        self.dp = xbmcgui.DialogProgress()
        self.dp.create(translate(32000), translate(32012))

        for url in urllist:
            if self.stop:
                break

            video_file = url.split("/")[-1]
            download_folder = addon.getSetting("download-folder")
            local_video_path = os.path.join(download_folder, video_file)

            if xbmcvfs.exists(local_video_path):
                xbmc.log(f"File {video_file} already exists, skip download", level=xbmc.LOGDEBUG)
                xbmcgui.Dialog().ok(
                    translate(32000),
                    f"{video_file} {translate(32038)}"
                )
                continue

            try:
                self.download(local_video_path, url, video_file)
            except (URLError, HTTPError) as e:
                xbmc.log(f"Error downloading {url}: {e}. Skipping to next file.", level=xbmc.LOGWARNING)
                self.dp.update(0, f"Failed to download {video_file}. Skipping...")
                xbmc.sleep(1500)

        if self.dp:
            self.dp.close()
            self.dp = None

    def download(self, path, url, name):
        xbmc.log(f"Starting multi-threaded download: {url}", level=xbmc.LOGDEBUG)

        if xbmcvfs.exists(path):
            try:
                xbmcvfs.delete(path)
            except Exception as e:
                xbmc.log(f"Failed to delete existing file {path}: {e}", level=xbmc.LOGERROR)

        self.dp.update(0, name)
        self.path = xbmcvfs.translatePath(path)
        xbmc.sleep(500)
        start_time = time.time()

        req = Request(url, method='HEAD', headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urlopen(req) as u:
                file_size = u.headers.get('Content-Length')
                if file_size is None:
                    xbmc.log("Keine Content-Length gefunden, lade sequentiell herunter.", level=xbmc.LOGWARNING)
                    self._simple_download(url, name, start_time)
                    return
                file_size = int(file_size)
        except Exception as e:
            xbmc.log(f"HEAD request failed: {e}, lade sequentiell herunter.", level=xbmc.LOGWARNING)
            self._simple_download(url, name, start_time)
            return

        segment_size = file_size // self.num_threads
        threads = []
        temp_files = [f"{self.path}.part{i}" for i in range(self.num_threads)]

        def download_segment(i, start, end):
            try:
                hdr = {'Range': f'bytes={start}-{end}', 'User-Agent': 'Mozilla/5.0'}
                req = Request(url, headers=hdr)
                with urlopen(req) as u, open(temp_files[i], 'wb') as f:
                    while not self.stop:
                        chunk = u.read(4096)
                        if not chunk:
                            break
                        f.write(chunk)
                xbmc.log(f"Segment {i} downloaded: {start}-{end}", level=xbmc.LOGDEBUG)
            except Exception as e:
                xbmc.log(f"Error downloading segment {i}: {e}", level=xbmc.LOGERROR)
                self.stop = True

        for i in range(self.num_threads):
            start_byte = i * segment_size
            end_byte = (start_byte + segment_size - 1) if i < self.num_threads - 1 else file_size - 1
            t = threading.Thread(target=download_segment, args=(i, start_byte, end_byte))
            threads.append(t)
            t.start()

        while any(t.is_alive() for t in threads):
            if self.stop:
                break
            downloaded = 0
            for fpath in temp_files:
                if os.path.exists(fpath):
                    downloaded += os.path.getsize(fpath)
            percent = int(downloaded * 100 / file_size)
            elapsed = time.time() - start_time
            speed = downloaded / elapsed if elapsed > 0 else 0
            eta = (file_size - downloaded) / speed if speed > 0 else 0
            speed_kbps = speed / 1024
            total_mb = file_size / (1024 * 1024)
            downloaded_mb = downloaded / (1024 * 1024)
            progress_text = (
                f"{name} - "
                f"{downloaded_mb:.2f} MB {translate(32008)} {total_mb:.2f} MB "
                f"({speed_kbps:.0f} KB/s)\n"
                f"{translate(32009)} {int(eta // 60):02d}:{int(eta % 60):02d}"
            )
            self.dp.update(percent, progress_text)
            xbmc.sleep(500)

        for t in threads:
            t.join()

        if self.stop:
            for fpath in temp_files:
                try:
                    os.remove(fpath)
                except Exception:
                    pass
            xbmc.log(f"Download canceled: {name}", level=xbmc.LOGDEBUG)
            return

        with open(self.path, 'wb') as output_file:
            for fpath in temp_files:
                with open(fpath, 'rb') as part_file:
                    output_file.write(part_file.read())
                try:
                    os.remove(fpath)
                except Exception:
                    pass

        xbmc.log(f"Download completed: {name}", level=xbmc.LOGDEBUG)

    def _simple_download(self, url, name, start_time):
        try:
            req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urlopen(req) as u, open(self.path, 'wb') as f:
                block_sz = 4096
                file_size = u.headers.get('Content-Length')
                file_size = int(file_size) if file_size else None
                file_size_dl = 0
                numblocks = 0

                while not self.stop:
                    buffer = u.read(block_sz)
                    if not buffer:
                        break

                    f.write(buffer)
                    file_size_dl += len(buffer)
                    numblocks += 1

                    try:
                        if file_size:
                            percent = int(min(file_size_dl * 100 / file_size, 100))
                        else:
                            percent = 0

                        downloaded_mb = file_size_dl / (1024 * 1024)
                        elapsed = time.time() - start_time
                        speed = file_size_dl / elapsed if elapsed > 0 else 0
                        eta = (file_size - file_size_dl) / speed if file_size and speed > 0 else 0
                        speed_kbps = speed / 1024
                        total_mb = file_size / (1024 * 1024) if file_size else 0

                        progress_text = (
                            f"{name} - "
                            f"{downloaded_mb:.2f} MB {translate(32008)} {total_mb:.2f} MB "
                            f"({speed_kbps:.0f} KB/s)\n"
                            f"{translate(32009)} {int(eta // 60):02d}:{int(eta % 60):02d}"
                        )
                        self.dp.update(percent, progress_text)
                    except Exception as e:
                        xbmc.log(f"Error updating progress: {e}", level=xbmc.LOGERROR)
                        self.dp.update(100)

                    if self.dp.iscanceled():
                        self.stop = True
                        break

            if self.stop:
                try:
                    os.remove(self.path)
                except Exception:
                    xbmc.log(f"Could not remove file {self.path} after cancel", level=xbmc.LOGERROR)
                xbmc.log(f"Download canceled: {name}", level=xbmc.LOGDEBUG)

        except Exception as e:
            xbmc.log(f"Exception during simple download {url}: {e}", level=xbmc.LOGERROR)
            raise
