# Matrix Screensaver for Kodi

Turns your idle Kodi screen into the Matrix: 17 hand-picked scenes from the
films, streamed in 1080p60 or played from local storage, shuffled into an
endless rotation.

---

## Features

- **17 scenes**, each individually switchable in the settings
- **1080p / 60 fps**, shuffled and looped for as long as the screensaver is up
- **Streaming or offline** — play straight from the web, or download the videos
  once (~5.85 GB in total) and never touch the network again
  - Download all scenes at once or one at a time
  - Downloads run over 8 parallel connections with progress, speed, ETA and cancel
  - Already downloaded videos are detected and skipped
  - Interrupted downloads leave no truncated files behind
- **Display power management (DPMS)** — after a configurable idle time the
  video is paused or stopped and the display is switched off or put into
  standby via HDMI-CEC
- Gets out of the way when something else is already playing
- English and German UI

## Requirements

- Any platform Kodi runs on
- An internet connection for streaming, or ~5.85 GB of free storage for
  offline mode

## Installation

1. Download the repository as a ZIP, or clone it and zip the
   `screensaver.matrix` folder.
2. In Kodi: **Settings → Add-ons → Install from zip file** and pick the ZIP.
   (Installing from a ZIP requires *Unknown sources* to be enabled under
   **Settings → System → Add-ons**.)
3. Activate it under **Settings → Interface → Screensaver → Screensaver mode →
   Matrix**.

For development you can also drop the folder straight into your Kodi
`addons/` directory and restart Kodi.

## Settings

### General

| Setting | Description |
| --- | --- |
| Show start notification | Toast when the screensaver kicks in |
| Show preview window | Shows a loading screen before playback starts |

### Offline mode

| Setting | Description |
| --- | --- |
| Download folder | Where the videos are stored |
| Only use local files | Full offline mode — no network calls at all, only downloaded videos are played |
| Download Videos | Opens the scene picker and starts the download |

Offline mode is strict on purpose: with **Only use local files** enabled, a
scene without a downloaded copy simply drops out of the rotation instead of
falling back to streaming. If nothing has been downloaded yet, the screensaver
shows *"No downloaded videos for offline mode!"*.

### DPMS

| Setting | Description |
| --- | --- |
| DPMS | `Off`, `Kodi` (reuse Kodi's own *Power saving → Turn off display* timeout) or `Manual` |
| Manual timeout | 5–120 minutes, in steps of 5 (only with `Manual`) |
| DPMS action | `Pause Video` keeps the window up, `Stop Video` tears it down and leaves a transparent placeholder so Kodi still counts as idle |
| Toggle display off | Runs Kodi's `ToggleDPMS` built-in |
| Put playing device on standby via CEC | Runs Kodi's `CECStandby` built-in |

### Videos

One toggle per scene: 3D, 3D (Alternative), Black & White, Bugs, Classic,
Classic (with Intro), Debug, Megacity (Revolutions), Morpheus, Nightmare,
Operator, Palimpsest, Paradise, Rainbow, Resurrections, Trinity, Twilight.

## How it works

A Kodi screensaver addon is only allowed to *draw*, not to play video. The
addon therefore registers three extension points and passes the work along:

| Extension point | Module | Job |
| --- | --- | --- |
| `xbmc.ui.screensaver` | `entrypoints/screensaver_entry.py` | Decides what Kodi gets to see, then hands over |
| `xbmc.python.script` | `entrypoints/script_entry.py` | Plays the videos, or opens the downloader when called with `offline` |
| `xbmc.service` | `entrypoints/service_entry.py` | Clears the `is_locked` flag once per Kodi start |

When the screensaver fires:

1. Something else is playing? → dismiss the screensaver and do nothing.
2. Our own video is already running (`is_locked`)? → show the transparent
   placeholder instead of starting playback twice.
3. Otherwise: optionally show the preview window, then `RunAddon` the script
   entry point, which opens the real video window and loops the shuffled
   playlist until the user presses a key or DPMS kicks in.

`is_locked` is an internal, hidden setting. It survives a crash during
playback, which is why the service resets it at every Kodi start.

## Project layout

Kodi only puts the running script's own directory on `sys.path`, so every entry
point adds `resources/lib` to it before importing anything; from there on all
imports are absolute (`from core.addon import ...`).

```
addon.xml
resources/
  settings.xml
  language/                the .po files (en_gb, de_de)
  playlist/playlist.json   scene names and video URLs
  skins/default/           the window definitions (720p and 1080i)
  lib/
    entrypoints/
      screensaver_entry.py   xbmc.ui.screensaver -- hands over to the script
      script_entry.py        xbmc.python.script  -- plays or downloads
      service_entry.py       xbmc.service        -- clears the lock at startup
    core/
      addon.py               settings, dialogs and translations
      logger.py              prefixed logging
      assets.py              the 17 scenes and their settings and labels
    gui/
      skin.py                window definitions and control ids
      screensaver.py         the window that plays the videos
      preview.py             the loading screen shown before playback starts
      transparent.py         placeholder shown while a video is already running
    playback/
      playlist.py            builds the shuffled rotation from playlist.json
      player.py              the xbmc.Player subclass used for playback
    download/
      picker.py              the "Download Videos" selection dialog
      downloader.py          parallel downloads with progress and cancel support
```

## Adding or changing a scene

Three files describe the same scenes and all three have to be touched:

1. `resources/playlist/playlist.json` — the `name` and the `video` URL
2. `resources/settings.xml` — one `enable-*` toggle
3. `resources/language/*/strings.po` — the setting label and the short label
   used by the download picker

`resources/lib/core/assets.py` maps the three sides together explicitly. The
names are **not** derived from each other — deriving the setting id from the
name used to break for every multi-word scene, so a new scene has to be added
to the `ASSETS` tuple as well. A scene that exists in `playlist.json` but not
in `assets.py` stays in the rotation and cannot be switched off.

## Troubleshooting

Every log line the addon writes is prefixed with `[Matrix Screensaver]`, so
filtering `kodi.log` for that string shows the whole story. Playback source and
startup time are logged at info level, so debug logging is not needed for the
common questions:

```
[Matrix Screensaver] Requesting network source: https://.../classic.mp4
[Matrix Screensaver] First frame after 1.83s, streamed over the network
```

| Symptom | Likely cause |
| --- | --- |
| Screensaver stays black / *"No downloaded videos"* | **Only use local files** is on but the download folder is empty or unset |
| Screensaver never starts | Another player is active, or `is_locked` is stuck — restart Kodi, the service clears it |
| First frame takes minutes | The video is being pulled in full instead of streamed — check the log line above |
| A scene never appears | Its toggle is off, or its entry in `playlist.json` has no video URL |

## Credits

Videos are hosted at
[CE-Repo/screensaver.matrix-videos](https://github.com/CE-Repo/screensaver.matrix-videos).
All footage belongs to its respective copyright holders; this addon only plays
it back.

## License

Released under the MIT License — see [LICENSE](LICENSE).
