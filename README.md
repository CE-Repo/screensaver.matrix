# Matrix Screensaver for Kodi

Turns your idle Kodi screen into the Matrix: 17 hand-picked scenes from the
films, streamed in 1080p60 or played from local storage, shuffled into an
endless rotation -- or a code rain the addon draws itself, without any video
file at all.

---

## Features

- **17 scenes**, each individually switchable in the settings
- **Live code rain**, a port of Rezmason's WebGL renderer drawn by the addon
  itself instead of played from a file: no video, no download, no network
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
| Variant of the code rain | Which version of the rain to draw, see below |
| Speed of the code rain | How fast the columns fall; `Normal` is the pace the variant itself sets |
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

It is a port of [Rezmason/matrix](https://github.com/Rezmason/matrix), the
WebGL project the videos were rendered with. Its shaders describe the effect as
two separate things: a grid of glyphs that **stay where they are**, and a
brightness that travels down **through** them. Getting that the right way round
is what makes the rain look alive rather than like a texture being dragged
across the screen.

Kodi's Python API has no drawing surface and no access to shaders, but it can
stack two images, which is enough to do the same thing inside out. Every column
is two controls:

* the **light** underneath: a narrow bar of colour, one band per grid row,
  scrolling downwards on a looping slide animation. It carries the raindrops
  and nothing else -- no glyphs at all.
* the **stencil** on top: black, with the column's glyphs punched out of it,
  and it never moves. The light is only ever visible in the shape of a glyph.

So the glyphs sit still and the light falls through them, exactly as in the
original, while the skin engine only has to move one control per column.

| Module | What it does |
| --- | --- |
| `render/raindrop.py` | The port itself: the raindrop wave, the wobble that varies drop lengths, the cursor at the head of each drop, and the palette |
| `render/version.py` | The variants, with the values each of them overrides in `js/config.js` of that project |
| `render/glyphs.py` | Cuts the 57 glyphs out of `resources/glyphs/`, the films' own glyph atlas. It is a distance field rather than a picture, so the module turns it into coverage maps with clean edges. A font would not do: Kodi resolves fonts against the active skin |
| `render/rain.py` | Builds and caches the stencil and light textures |
| `render/png.py` | A minimal PNG codec, because Kodi ships no imaging library |
| `gui/rain.py` | Puts the controls on screen and gives each light its animation |

Every variant brings its own grid, so the shape of both textures is worked out
from its settings: the classic grid is 45 glyphs tall, which puts 80 columns on
a 16:9 screen. The window derives the column count from the aspect ratio, so the
cells keep their shape from 720p up to ultra-wide. Each column falls at a speed
of its own, between half and full, the way the shader picks it; `Speed of the
code rain` scales the whole range. Generating a variant's 224 textures takes
about a second and only happens once: they are cached per variant in the
addon's profile folder (`addon_data/screensaver.matrix/rain/<variant>`) and
reused from there, and textures left behind by an older version are cleaned out.

### Variants

`Variant of the code rain` picks between the versions of the effect, with the
glyphs, colours, density and speed each of them configures in that project:

| Variant | Glyphs | What it looks like |
| --- | --- | --- |
| Classic | matrixcode | The green rain of the films |
| Megacity | megacity | The same green, twice the size |
| Nightmare | gothic | Dark red, fast and short |
| Operator | matrixcode | Dense, tall cells, glyphs that switch on rather than fade |
| Palimpsest | huberfishA | Dark glyphs on a light page |
| Paradise | coptic | Gold and orange, drifting down very slowly |
| Rainbow | matrixcode | The classic rain, coloured in vertical stripes |
| Resurrections | resurrections | The greens of the fourth film |
| Twilight | huberfishD | Blue, pink and gold |

Variants built on perspective (3D, Trinity, Morpheus, Bugs) are not there:
those draw their grid in depth, which a stack of flat images cannot do. Of the
listed ones, Paradise drops the curved grid and the ripples, Operator the
ripples, Nightmare the thunder, and Nightmare and Palimpsest the slanted grid.
Nightmare leans on its thunder to light the screen up, so without it the
variant stays dark -- which is what its raw output looks like.

### Where the port stops

Three things in the original need per-frame, per-glyph work that a scrolling
texture cannot do, and they are left out:

* **Glyphs do not change.** In the original every glyph swaps for another one
  about twice a second. Here the stencil is a fixed image, so a column keeps
  its glyphs for as long as the screensaver runs.
* **No bloom.** The original blurs the bright parts back over the image, which
  is a second render pass.
* **The wobble repeats.** Its two sine waves run at sqrt(2) and sqrt(5) and so
  never line up again; a texture has to. They are moved onto the nearest whole
  number of cycles per loop, which stays within a tenth of the originals and
  keeps the drop lengths varied, but a column does repeat itself after a
  handful of raindrops.

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
  glyphs/                  the glyph atlases of the code rain, and their licence
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
      raindrop.py            the ported rain algorithm: waves, cursors, palette
      version.py             the variants and the glyph atlas each one uses
      glyphs.py              cuts the glyphs out of the distance field atlas
      rain.py                builds and caches the stencil and light textures
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

The live code rain is a port of [Rezmason/matrix](https://github.com/Rezmason/matrix),
MIT licensed, copyright (c) 2018 Rezmason -- the algorithm in
`resources/lib/render/raindrop.py`, the variants in `render/version.py`, and
the glyph atlases in `resources/glyphs/`, which are taken from it unchanged.
The atlases carry their licence text next to them, and that has to stay with
the files. That project is also where the videos
were rendered.

Videos are hosted at
[CE-Repo/screensaver.matrix-videos](https://github.com/CE-Repo/screensaver.matrix-videos).
All footage belongs to its respective copyright holders; this addon only plays
it back.

## License

Released under the MIT License — see [LICENSE](LICENSE).
