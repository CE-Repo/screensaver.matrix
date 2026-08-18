# Matrix Screensaver for Kodi

Turns your idle Kodi screen into the Matrix. The code rain is drawn by the
addon itself -- no video files, no downloads, no network -- as a port of
[Rezmason/matrix](https://github.com/Rezmason/matrix), with fourteen of its
variants taking turns.

---

## Features

- **The code rain, generated**: nothing is played back, everything is drawn
- **14 variants** from Rezmason's project, each with its own glyphs, colours,
  density and speed, and each switchable on its own
- **They take turns**: one is picked at random, held for as long as you like,
  then the next
- **Display power management (DPMS)** -- after a configurable idle time the
  scene is stopped and the display is switched off or put into standby via
  HDMI-CEC
- Gets out of the way when something else is already playing
- English and German UI

## Requirements

- Any platform Kodi runs on. No internet connection and no storage worth
  mentioning: the addon ships 680 KB of glyph atlases and generates about a
  megabyte of textures per variant into its own profile folder.

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
| Show preview window | Shows a loading screen before the rain starts |

### Code rain

| Setting | Description |
| --- | --- |
| Minutes per variant | How long one variant stays up before the next is picked, 1 to 60. Zero, at the left end of the slider, keeps the one it started with |
| Speed of the code rain | Scales the pace every variant sets for itself |

### DPMS

| Setting | Description |
| --- | --- |
| Check DPMS | Off, follow Kodi's power saving timeout, or a manual one |
| Action | Whether the scene is paused or stopped when the timeout hits |
| Turn off display / CEC standby | What to do with the screen |

### Variants

One toggle per variant. The screensaver picks at random from the ones left
switched on, so switching all but one off pins it to that variant. With none
switched on it falls back to Classic. Debug is off to begin with -- it is a
tool, not a scene.

Picking one at random every time is the obvious approach and the wrong one: it
lands on the variant already showing far too often -- with four enabled, every
fourth pick, sometimes three or four times over -- while another stays away for
ages. The addon draws from a shuffled pass instead, so every variant gets its
turn before any of them comes round again. The one place a repeat could still
slip through is where two passes meet, so a pass that would open on the variant
just shown swaps it for another, and the variant last seen is remembered across
screensaver runs so a restart cannot repeat it either.

## The variants

| Variant | Glyphs | What it looks like | Left out |
| --- | --- | --- | --- |
| 3D | matrixcode | Columns rushing past the viewer, out of a vanishing point | glyph churn |
| Bugs | resurrections | Amber and yellow | perspective, glint |
| Classic | matrixcode | The green rain of the films | -- |
| Debug | matrixcode | What the raindrop pass computes: red cursors, brightness across two channels | -- |
| Megacity | megacity | The same green, twice the size | -- |
| Morpheus | resurrections | Deep red and magenta | perspective, glint |
| Nightmare | gothic | Dark red, fast, with short drops | thunder, slant |
| Operator | matrixcode | Dense, tall cells, glyphs that switch on rather than fade | ripples |
| Palimpsest | huberfishA | Dark glyphs on a light page | slant |
| Paradise | coptic | Gold and orange, drifting down very slowly | curved grid, ripples |
| Rainbow | matrixcode | The classic rain, coloured in vertical stripes | -- |
| Resurrections | resurrections | The greens of the fourth film | -- |
| Trinity | resurrections | Muted green | perspective, glint |
| Twilight | huberfishD | Blue, pink and gold | -- |

Four of these are drawn in perspective in the original: 3D, Trinity, Morpheus
and Bugs. 3D is drawn that way here too, as columns flying past -- see below.
The other three are drawn flat, with everything else they configure intact;
turning them into flights as well is one flag each in `render/version.py`.
Nightmare leans on its thunder to light the screen up, so without it the
variant stays dark; that is what its raw output looks like.

## How it works

A Kodi screensaver addon may only draw a window, and Kodi tears that window
down again the moment the screensaver deactivates. The addon therefore
registers three extension points and passes the work along:

| Extension point | Module | Job |
| --- | --- | --- |
| `xbmc.ui.screensaver` | `entrypoints/screensaver_entry.py` | Decides what Kodi gets to see, then hands over |
| `xbmc.python.script` | `entrypoints/script_entry.py` | Opens the window the rain runs in |
| `xbmc.service` | `entrypoints/service_entry.py` | Clears the `is_locked` flag once per Kodi start |

When the screensaver fires:

1. Something else is playing? -> dismiss the screensaver and do nothing.
2. Our own window is already up (`is_locked`)? -> show the transparent
   placeholder instead of starting over.
3. Otherwise: optionally show the preview window, then `RunAddon` the script
   entry point, which opens the rain window.

`is_locked` is an internal, hidden setting. It survives a crash, which is why
the service resets it at every Kodi start.

## The code rain

Rezmason's shaders describe the effect as two separate things: a grid of glyphs
that **stay where they are**, and a brightness that travels down **through**
them. Getting that the right way round is what makes the rain look alive rather
than like a texture being dragged across the screen.

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
| `render/glyphs.py` | Cuts the glyphs out of the atlases in `resources/glyphs/`. They are distance fields rather than pictures, so the module turns them into coverage maps with clean edges. A font would not do: Kodi resolves fonts against the active skin |
| `render/rain.py` | Builds and caches the stencil and light textures |
| `render/png.py` | A minimal PNG codec, because Kodi ships no imaging library |
| `gui/rain.py` | Puts the controls on screen, gives each light its animation, and swaps variants |

Every variant brings its own grid, so the shape of both textures is worked out
from its settings: the classic grid is 45 glyphs tall, which puts 80 columns on
a 16:9 screen. The window derives the column count from the aspect ratio, so
the cells keep their shape from a 720p screen up to ultra-wide. Each column falls at a
speed of its own, between half and full, the way the shader picks it.

Generating a variant's 224 textures takes about a second and only happens once:
they are cached per variant in the addon's profile folder
(`addon_data/screensaver.matrix/rain/<variant>`) and reused from there, and
textures left behind by an older version are cleaned out. The variant coming up
is built while the current one is still on screen, so the change itself is
immediate, and it happens behind a black cover that fades over the picture and
back off it. The skin engine cannot run that fade: its animations react to
conditions rather than to a moment of our choosing, so the cover is dimmed from
Python in two dozen steps, eased at both ends.

### Columns that come at you

3D does not tile the screen. It puts 40 columns in the air, each one where it
would stand at a reference depth, and grows it about the middle of the screen.
Growing about a point is exactly what approaching one looks like: a column
swells and, because the point it grows around is the vanishing point, drifts
outwards until it passes the edge of the screen. The light and the stencil are
given the same growth, so the glyphs stay put inside a column while it comes at
you, and the light still falls through them.

Two things about Kodi's animations shape how this is built:

* **A column gets one approach, not a loop.** A looped animation rewinds the
  same control, so at the end of every cycle all 40 would snap back to the
  vanishing point together. Each column is given a single trip instead and
  replaced by a new one when it is over, which `gui/rain.py` does about five
  times a second while the variant is up.
* **They start part-way along.** There is no way to offset an animation in
  time -- a `delay` is served again on every loop, so it is a pause and not an
  offset -- so a column that should already be halfway there is simply built
  halfway there, with a trip shortened to match. That is what fills the screen
  with columns at every depth from the first frame.

A column is furthest from the axis when it is nearest, so how far it grows
follows from where it stands: far enough that its inner edge has passed the
edge of the screen, plus a tenth so it is gone before it is taken away. Nothing
stands near the axis, because a column there would still be on screen when it
had grown as far as it may. Its texture is stretched over four times its own
size by then, which is as soft as it looks -- the stencils are drawn at 22
pixels per glyph, and a texture tall enough to hold 45 of them at four times
that would not fit the 2048 pixel limit.

### Where the port stops

Three things in the original need per-frame, per-glyph work that a scrolling
texture cannot do, and they are left out of every variant:

* **Glyphs do not change.** In the original every glyph swaps for another one
  about twice a second. Here the stencil is a fixed image, so a column keeps
  its glyphs for as long as it is on screen.
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
  glyphs/                  the glyph atlases of the code rain, and their licence
  skins/default/           the window definitions (1080i, scaled by Kodi)
  lib/
    entrypoints/
      screensaver_entry.py   xbmc.ui.screensaver -- hands over to the script
      script_entry.py        xbmc.python.script  -- opens the rain window
      service_entry.py       xbmc.service        -- clears the lock at startup
    core/
      addon.py               settings, dialogs and translations
      logger.py              prefixed logging
    gui/
      skin.py                window definitions and control ids
      base.py                what the screensaver windows have in common
      rain.py                the rain window, and the variants taking turns
      preview.py             the loading screen shown before the rain starts
      transparent.py         placeholder shown while the rain is already up
    render/
      raindrop.py            the ported rain algorithm: waves, cursors, palette
      version.py             the variants and the glyph atlas each one uses
      glyphs.py              cuts the glyphs out of the distance field atlases
      rain.py                builds and caches the stencil and light textures
      png.py                 minimal PNG codec for the atlases and the textures
```

## Adding a variant

1. `resources/lib/render/version.py` -- one `Version(...)` entry with the values
   it overrides, exactly as `js/config.js` in Rezmason's project spells them.
   Its `setting_id` follows from its name.
2. `resources/glyphs/` -- the atlas, if it uses one that is not there yet, plus
   a row in that folder's README and an entry in `FONTS`.
3. `resources/settings.xml` -- one toggle, `enable-<name>`.
4. `resources/language/*/strings.po` -- the label the toggle shows.

Everything else follows: the grid, the raindrop length, the texture shapes and
the cache folder are all worked out from the entry.

## Troubleshooting

Every log line the addon writes is prefixed with `[Matrix Screensaver]`, so
filtering `kodi.log` for that string shows the whole story:

```
[Matrix Screensaver] Code rain: paradise in 39 columns
```

| Symptom | Likely cause |
| --- | --- |
| Screensaver never starts | Another player is active, or `is_locked` is stuck -- restart Kodi, the service clears it |
| A long pause before the first frame | The textures of that variant are being generated; it happens once per variant and the loading screen shows the progress |
| *"The code rain could not be generated"* | The profile folder is not writable |
| Always the same variant | Minutes per variant is 0, only one variant is switched on, or all of them are off and it fell back to Classic |
| One variant looks far darker than the rest | Nightmare, which relies on the thunder effect that is not ported |

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
the files.

## License

Released under the MIT License -- see [LICENSE](LICENSE).
