# Matrix Screensaver for Kodi

Turns your idle Kodi screen into the Matrix: 17 hand-picked scenes from the
films, streamed in 1080p60 or played from local storage, shuffled into an
endless rotation -- or a code rain the addon draws itself, without any video
file at all.

---

## Features

- **17 scenes**, each individually switchable in the settings
- **Live code rain**, drawn by the addon with the films' own glyphs instead of
  played from a file: no video, no download, no network, and it starts instantly
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
- For the video scenes: an internet connection for streaming, or ~5.85 GB of
  free storage for offline mode. The live code rain needs neither.

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
| Scene | `Videos` plays the clips, `Live code rain (generated)` draws the rain instead |
| Speed of the code rain | How fast the columns fall; `Normal` matches the rendered videos |
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

## The live code rain

The scenes from the films are video, but the classic code rain does not have to
be: with `Scene` set to `Live code rain (generated)` the addon draws it itself.
The same happens automatically when the video rotation ends up empty -- offline
mode with nothing downloaded, or every scene switched off -- so the screen shows
the Matrix instead of a message.

Kodi's Python API has no drawing surface and no access to shaders, so the rain
is built out of the two things a Python addon does have: image controls and the
skin engine's animations.

1. `render/glyphs.py` cuts the 57 glyphs out of `resources/glyphs/`, the
   films' own glyph atlas from [Rezmason/matrix](https://github.com/Rezmason/matrix).
   The atlas is a distance field rather than a picture, so the module first
   turns it into coverage maps with clean, smooth edges. A font would not do
   here: Kodi resolves fonts against the active skin, and these characters are
   not part of it.
2. `render/rain.py` assembles those glyphs into one texture per column --
   trails that fade out behind a bright head, a few faint background glyphs,
   and the whole pattern stacked twice so it can scroll seamlessly. The
   textures are written with a small PNG encoder in `render/png.py`, because
   Kodi ships no imaging library.
3. `gui/rain.py` puts one image control per column on screen and gives each a
   looping slide animation that travels exactly one screen height, at a speed
   of its own.

Each column falls one screen height every 1.5 to 3 seconds, which is the pace
Rezmason's renderer sets: its columns advance 100 * `fallSpeed` glyphs per
second, scaled per column by a random 0.5 to 1.0. The `Speed of the code rain`
setting scales that range.

From then on the skin engine moves the columns, so the rain runs at the skin's
frame rate with no per-frame work in Python at all. The grid is 45 glyphs tall,
which puts 80 columns on a 16:9 screen -- the same density Rezmason's renderer
uses by default -- and the window derives the column count from the aspect
ratio, so the glyphs stay square from 720p up to ultra-wide. Generating all 112
textures takes about a second and only happens once: they are cached in the
addon's profile folder (`addon_data/screensaver.matrix/rain`) and reused from
there, and textures left behind by an older version are cleaned out.

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
  glyphs/                  the glyph atlas of the code rain, and its licence
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
      base.py                what both screensaver windows have in common
      screensaver.py         the window that plays the videos, and the scene choice
      rain.py                the window that draws the live code rain
      preview.py             the loading screen shown before playback starts
      transparent.py         placeholder shown while a video is already running
    playback/
      playlist.py            builds the shuffled rotation from playlist.json
      player.py              the xbmc.Player subclass used for playback
    render/
      glyphs.py              cuts the glyphs out of the distance field atlas
      rain.py                builds and caches the column textures
      png.py                 minimal PNG codec for the atlas and the textures
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


## Screenshots

<p align="center">
<img width="800" alt="screenshot-01" src="https://github.com/user-attachments/assets/2844c79f-9b08-4b3a-9f36-eac0bfc298a9" />
</p>

<p align="center">
<img width="800" alt="screenshot-02" src="https://github.com/user-attachments/assets/8cd4679a-1d92-45c3-b3b4-f818bd6ebc47" />
</p>

<p align="center">
<img width="800" alt="screenshot-03" src="https://github.com/user-attachments/assets/59a22ec1-f2ac-435f-8b55-0cdb9b961116" />
</p>

<p align="center">
<img width="800" alt="screenshot-04" src="https://github.com/user-attachments/assets/1fdec033-f8f1-46e4-85ad-edadaa7eecbc" />
</p>

## Credits

The glyph atlas in `resources/glyphs/` is taken unchanged from
[Rezmason/matrix](https://github.com/Rezmason/matrix), MIT licensed, copyright
(c) 2018 Rezmason. Its licence text sits next to it and has to stay with the
file. That project is also where the videos were rendered.

Videos are hosted at
[CE-Repo/screensaver.matrix-videos](https://github.com/CE-Repo/screensaver.matrix-videos).
All footage belongs to its respective copyright holders; this addon only plays
it back.

## License

Released under the MIT License — see [LICENSE](LICENSE).
