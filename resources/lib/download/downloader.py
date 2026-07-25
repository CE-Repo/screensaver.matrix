"""Downloads the Matrix videos into the configured folder for offline playback."""

import os
import shutil
import threading
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

import xbmc
import xbmcgui
import xbmcvfs

from core import logger
from core.addon import ok_dialog, translate
from core.assets import file_name_for

#: Sent with every request; the default urllib agent is rejected by some CDNs
HEADERS = {"User-Agent": "Mozilla/5.0"}

#: Seconds to wait for the server before a request is considered dead
TIMEOUT = 30

#: Bytes read per iteration
CHUNK_SIZE = 64 * 1024

#: Parallel range requests used per video
THREAD_COUNT = 8

#: Smallest file worth splitting across THREAD_COUNT connections
MIN_PARALLEL_SIZE = THREAD_COUNT * CHUNK_SIZE

#: How often the progress dialog is refreshed, in seconds
PROGRESS_INTERVAL = 0.5

MEGABYTE = 1024 * 1024

#: Status code a server returns when it honours a Range request
PARTIAL_CONTENT = 206


def file_size(path):
    """Size of *path* in bytes, 0 if it does not exist yet."""
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def remove_file(path):
    """Delete *path* if it exists, logging instead of raising on failure."""
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError as exc:
        logger.warning("Could not remove {}: {}".format(path, exc))


class Downloader:
    """Fetches a list of video URLs into *folder*.

    Every video is written to a ``.part`` file and only renamed once its length
    matches what the server announced, so an interrupted download can never
    leave behind a truncated file that later looks like a finished one.
    """

    def __init__(self, folder):
        self.folder = folder
        self.dialog = None
        self.cancelled = False

    # -- Public API -------------------------------------------------------

    def download_all(self, urls):
        """Download every URL, skipping videos that are already present."""
        self.dialog = xbmcgui.DialogProgress()
        self.dialog.create(translate(32000), translate(32012))

        completed, skipped, failed = 0, [], []
        try:
            for url in urls:
                if self.cancelled:
                    break
                name = file_name_for(url)
                target = os.path.join(self.folder, name)

                if xbmcvfs.exists(target):
                    logger.debug("{} already exists, skipping".format(name))
                    skipped.append(name)
                    continue

                try:
                    if self.download(url, target, name):
                        completed += 1
                    elif not self.cancelled:
                        failed.append(name)
                except Exception as exc:
                    # One unreachable video must not abort the whole batch.
                    logger.error("Downloading {} failed: {}".format(url, exc))
                    failed.append(name)
                    self.dialog.update(0, "{} {}".format(translate(32076), name))
                    xbmc.sleep(1500)
        finally:
            self.dialog.close()
            self.dialog = None

        logger.info("Downloaded {}, skipped {}, failed {}".format(
            completed, len(skipped), len(failed)))
        self.report(completed, skipped, failed)

    # -- One video --------------------------------------------------------

    def download(self, url, target, name):
        """Fetch a single video. True when the file arrived complete."""
        logger.debug("Starting download: {}".format(url))
        self.dialog.update(0, name)

        size, ranges_supported = self.probe(url)
        started_at = time.time()
        temp_path = target + ".part"
        remove_file(temp_path)

        if size and ranges_supported and size >= MIN_PARALLEL_SIZE:
            complete = self.download_in_parallel(url, temp_path, name, size, started_at)
        else:
            complete = self.download_sequentially(url, temp_path, name, size, started_at)

        written = file_size(temp_path)
        if complete and size and written != size:
            logger.error("{} is incomplete: {} of {} bytes".format(name, written, size))
            complete = False

        if not complete:
            remove_file(temp_path)
            return False

        os.replace(temp_path, target)
        logger.info("Download completed: {} ({:.1f} MB in {:.0f}s)".format(
            name, written / MEGABYTE, time.time() - started_at))
        return True

    @staticmethod
    def probe(url):
        """Return ``(content length or None, whether ranges are supported)``."""
        try:
            request = Request(url, method="HEAD", headers=HEADERS)
            with urlopen(request, timeout=TIMEOUT) as response:
                length = response.headers.get("Content-Length")
                accepts = response.headers.get("Accept-Ranges", "").lower()
                return (int(length) if length else None, accepts == "bytes")
        except (OSError, ValueError) as exc:  # URLError and HTTPError are OSErrors
            logger.warning("HEAD request for {} failed ({}), downloading in one piece"
                           .format(url, exc))
            return (None, False)

    def download_in_parallel(self, url, temp_path, name, size, started_at):
        """Fetch *size* bytes with THREAD_COUNT range requests, then join them."""
        segment = size // THREAD_COUNT
        parts = []
        threads = []
        abort = threading.Event()
        failures = []

        for index in range(THREAD_COUNT):
            start = index * segment
            end = size - 1 if index == THREAD_COUNT - 1 else start + segment - 1
            part_path = "{}.{}".format(temp_path, index)
            parts.append((part_path, end - start + 1))
            thread = threading.Thread(
                target=self.fetch_range,
                args=(url, part_path, start, end, abort, failures),
                daemon=True)
            threads.append(thread)
            thread.start()

        try:
            while any(thread.is_alive() for thread in threads):
                if self.dialog.iscanceled():
                    self.cancelled = True
                    abort.set()
                    break
                self.show_progress(
                    name, sum(file_size(path) for path, _ in parts), size, started_at)
                xbmc.sleep(int(PROGRESS_INTERVAL * 1000))

            for thread in threads:
                thread.join()

            if abort.is_set() or failures:
                return False

            for part_path, expected in parts:
                if file_size(part_path) != expected:
                    logger.error("Segment {} of {} is truncated".format(part_path, name))
                    return False

            self.show_progress(name, size, size, started_at)
            with open(temp_path, "wb") as output:
                for part_path, _ in parts:
                    with open(part_path, "rb") as part:
                        shutil.copyfileobj(part, output, CHUNK_SIZE)
            return True
        finally:
            for part_path, _ in parts:
                remove_file(part_path)

    @staticmethod
    def fetch_range(url, path, start, end, abort, failures):
        """Download one byte range into *path*, setting *abort* if it fails."""
        try:
            headers = dict(HEADERS, Range="bytes={}-{}".format(start, end))
            with urlopen(Request(url, headers=headers), timeout=TIMEOUT) as response:
                if response.getcode() != PARTIAL_CONTENT:
                    # Without this check a server that ignores Range would send
                    # the whole file to every thread and the parts would be
                    # concatenated into a file eight times too long.
                    raise URLError("server ignored the range request")
                with open(path, "wb") as part:
                    while not abort.is_set():
                        chunk = response.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        part.write(chunk)
        except Exception as exc:
            if not abort.is_set():
                logger.error("Range {}-{} failed: {}".format(start, end, exc))
            failures.append(path)
            abort.set()

    def download_sequentially(self, url, temp_path, name, size, started_at):
        """Fetch the whole file over a single connection."""
        last_update = 0.0
        with urlopen(Request(url, headers=HEADERS), timeout=TIMEOUT) as response:
            with open(temp_path, "wb") as output:
                done = 0
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    output.write(chunk)
                    done += len(chunk)

                    now = time.time()
                    if now - last_update >= PROGRESS_INTERVAL:
                        last_update = now
                        self.show_progress(name, done, size, started_at)
                        if self.dialog.iscanceled():
                            self.cancelled = True
                            return False
        return True

    # -- Reporting --------------------------------------------------------

    def show_progress(self, name, done, size, started_at):
        """Refresh the progress dialog with speed and remaining time."""
        elapsed = time.time() - started_at
        speed = done / elapsed if elapsed > 0 else 0
        if size:
            percent = min(100, max(0, int(done * 100 / size)))
            total_mb = size / MEGABYTE
            remaining = (size - done) / speed if speed > 0 else 0
        else:
            percent, total_mb, remaining = 0, 0, 0

        self.dialog.update(percent, (
            "{} - {:.2f} MB {} {:.2f} MB ({:.0f} KB/s)\n{} {:02d}:{:02d}".format(
                name, done / MEGABYTE, translate(32008), total_mb, speed / 1024,
                translate(32009), int(remaining // 60), int(remaining % 60))))

    @staticmethod
    def report(completed, skipped, failed):
        """Tell the user about failures, or that there was nothing left to do."""
        lines = []
        if failed:
            lines.append("{} {}".format(translate(32076), ", ".join(failed)))
        elif skipped and not completed:
            lines.append(translate(32075))
        if lines:
            ok_dialog(translate(32000), "\n".join(lines))
