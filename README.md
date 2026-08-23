# Matrix Screensaver for Kodi

Turns your idle Kodi screen into the Matrix. The code rain is drawn by the
addon itself -- no video files, no downloads, no network -- as a port of
[Rezmason/matrix](https://github.com/Rezmason/matrix), with thirteen of its
variants and nine of the addon's own taking turns -- one of them a 3D tunnel
the glyphs come flying out of.

---

## Features

- **The code rain, generated**: nothing is played back, everything is drawn
- **22 variants** -- thirteen from Rezmason's project and nine of this addon's
  own -- each with its own glyphs, colours, density and speed, and each
  switchable on its own
- **A 3D tunnel**: the rain keeps falling, but you fly into it -- 128 columns
  of glyphs at 128 depths come at you out of the distance, built the way
  Rezmason's volumetric mode is. Same glyphs, same colours, a scene of its own
- **The glyphs cycle**, the way they do in the films
- **They take turns**: one is picked at random, held for as long as you like,
  then the next
- **Display power management (DPMS)** -- after a configurable idle time the
  scene is stopped and the display is switched off or put into standby via
  HDMI-CEC
- Gets out of the way when something else is already playing
- UI in English, German, French, Spanish, Italian, Dutch, Polish and Russian

## Requirements

- Any platform Kodi runs on. No internet connection: the addon ships 680 KB of
  glyph atlases and generates its textures itself. All twenty-two variants
  together come to 75 MB in the profile folder, or 26 MB with the glyphs left
  as they are -- a variant is only ever built once, and only if it is switched
  on.

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
| Let the glyphs change | Glyphs swap for others now and then; switching it off saves two thirds of the cache |
| Prepare textures now | Builds every switched-on variant in one go, and drops the switched-off ones from the cache |

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

### From Rezmason's project

| Variant | Glyphs | What it looks like | Left out |
| --- | --- | --- | --- |
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

### This addon's own

Not from `js/config.js`: the same drawing parameters, set for looks the ported
variants do not cover. None of them needs an effect the port lacks.

| Variant | Glyphs | What it looks like |
| --- | --- | --- |
| Amber | matrixcode | A phosphor terminal: glyphs that switch on rather than fade, in amber |
| Blueprint | huberfishA | Cyan on a navy page that never goes fully black |
| Downpour | resurrections | A cloudburst: 112 narrow columns, short drops, a fast fall |
| Ember | coptic | Coals: long drops drifting down, with no cursor to break them up |
| Glacier | huberfishD | Pale ice, the slowest and quietest of them all |
| Neon | megacity | The megacity grid, striped in a magenta to cyan gradient |
| Noir | matrixcode | No colour at all: grey at a hard contrast, with a white cursor |
| Tunnel (3D) | matrixcode | The other scene: raindrops coming at the viewer out of the distance, falling as they come |
| Whiteout | gothic | Dark ink on a light page |

Trinity, Morpheus and Bugs are drawn in perspective in the original, which a
stack of flat images cannot do; they are drawn flat here, with everything else
they configure intact. Nightmare leans on its thunder to light the screen up
and Paradise on its bloom, and neither is ported, so both would be nearly black
on their own. They are the only two whose brightness is raised to stand in for
what is missing -- `lift` in `render/version.py`; everything else is drawn at
the brightness the shader computes.

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
| `render/version.py` | The variants: the ported ones with the values they override in `js/config.js` of that project, and this addon's own below them |
| `render/glyphs.py` | Cuts the glyphs out of the atlases in `resources/glyphs/`. They are distance fields rather than pictures, so the module turns them into coverage maps with clean edges. A font would not do: Kodi resolves fonts against the active skin |
| `render/rain.py` | Builds and caches the stencil and light textures |
| `render/tunnel.py` | Builds and caches the strips of the 3D tunnel: one raindrop each, on a transparent ground |
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

### The 3D tunnel

The tunnel is built the way Rezmason's volumetric mode is: not as a picture
that grows, but as many columns that each have a depth of their own. There,
every column of the rain is a quad with its own starting depth, cycling towards
the camera -- `quadDepth = fract(startDepth + time * forwardSpeed)` in
`rainPass.vert.glsl`. What fills the screen is how many columns are in the air,
not how large any one of them is.

Here a column is a narrow strip holding a single raindrop, transparent
everywhere else, and 128 of them are on screen at once. The whole perspective
is one zoom taken about the middle of the screen rather than about the control:
that grows the column and carries it away from the vanishing point by the same
factor, so a column far off is small and near the middle, and the same column
close up is large and out at the edge. A flight takes four and a half seconds
at the normal speed setting, and the "Speed of the code rain" setting scales it
the way it scales the fall. It rains while it comes, on a slide that shares the
zoom's period -- more than a screen and a half of fall per flight, and faster
the nearer it gets, because that slide is scaled up along with the column. And
it fades up out of the distance and back down as it passes, which is what hides
the moment both start over, fall included.

The columns sit on a jittered grid rather than at random, because a hundred odd
columns thrown at random leave holes big enough to see, and the eye reads a hole
as a fault rather than as chance. Their depths are handed out in coprime steps
across that grid, so depth and place stay unrelated; otherwise the grid would
arrive as a wave sweeping over the screen.

Depth is the zoom and the fade, not a projection: the strips are flat, they do
not turn, and their stacking order stays as it is while their depth changes. On
a black ground with drops this narrow, none of that shows. What it costs is one
control and three animations per column, and nothing per frame.

### Where the port stops

Three things in the original need per-frame, per-glyph work that a scrolling
texture cannot do, and they are left out of every variant:

* **Glyphs change, but far more slowly.** In the original every glyph swaps
  for another one about twice a second. A stencil holds a whole column, so a
  column is swapped between three of them instead, each differing from the
  last in about a seventh of its glyphs. Eight columns a second are swapped,
  which comes to roughly sixty glyphs a second across the screen against the
  several thousand the original manages.
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
  language/                the .po files (en_gb is the source, seven translations)
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
      rain.py                the rain and tunnel windows, and the variants taking turns
      prepare.py             the "prepare textures now" action from the settings
      preview.py             the loading screen shown before the rain starts
      transparent.py         placeholder shown while the rain is already up
    render/
      raindrop.py            the ported rain algorithm: waves, cursors, palette
      version.py             the variants and the glyph atlas each one uses
      glyphs.py              cuts the glyphs out of the distance field atlases
      rain.py                builds and caches the stencil and light textures
      tunnel.py              builds and caches the strips of the 3D tunnel
      png.py                 minimal PNG codec for the atlases and the textures
```

## Adding a variant

1. `resources/lib/render/version.py` -- one `Version(...)` entry with the values
   it overrides, exactly as `js/config.js` in Rezmason's project spells them.
   Its `setting_id` follows from its name, and `scene` picks which of the two
   it is drawn as.
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
| One variant looks far darker than the rest | Nightmare and Paradise rely on effects that are not ported; they are lifted, but only so far |
| The profile folder is large | Every variant that has been shown is cached; `Prepare textures now` drops the ones that are switched off, and `Let the glyphs change` off cuts the rest by two thirds |

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
