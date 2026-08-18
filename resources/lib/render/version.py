"""The versions of the code rain, as Rezmason's project configures them.

Every entry below is one of the variants from ``js/config.js`` in that project,
with the values it overrides copied across. What a variant cannot bring along
is noted next to it: the effects that need perspective, a curved grid, a second
render pass or per-frame work on single glyphs have no equivalent here, so
those variants are drawn flat, with everything else they configure intact.
"""

from collections import namedtuple

from render.raindrop import hsl

#: A glyph atlas: the file in resources/glyphs and the grid it is laid out on
Font = namedtuple("Font", ("file_name", "columns", "rows"))

FONTS = {
    "matrixcode": Font("matrixcode_msdf.png", 8, 8),
    "megacity": Font("megacity_msdf.png", 8, 8),
    "gothic": Font("gothic_msdf.png", 8, 8),
    "coptic": Font("coptic_msdf.png", 8, 8),
    "resurrections": Font("resurrections_msdf.png", 13, 12),
    "huberfishA": Font("huberfish_a_msdf.png", 6, 6),
    "huberfishD": Font("huberfish_d_msdf.png", 6, 6),
}

#: The default palette: the greens of the films
GREEN_PALETTE = (
    (0.0, hsl(0.3, 0.9, 0.0)),
    (0.2, hsl(0.3, 0.9, 0.2)),
    (0.7, hsl(0.3, 0.9, 0.7)),
    (0.8, hsl(0.3, 0.9, 0.8)),
)

#: The stripe colours of the rainbow variant, each held over two entries the
#: way the original builds its stripe texture
PRIDE_STRIPES = tuple(
    colour for colour in (
        (227, 3, 3), (255, 140, 0), (255, 237, 0),
        (0, 128, 38), (0, 77, 255), (117, 8, 135),
    ) for _ in range(2)
)

#: Everything a version may override, with the values from the project's own
#: defaults block
DEFAULTS = {
    "font": "matrixcode",
    #: Glyphs across a 16:9 screen
    "columns": 80,
    "animation_speed": 1.0,
    "fall_speed": 0.3,
    "raindrop_length": 0.75,
    "base_contrast": 1.1,
    "base_brightness": -0.5,
    #: Set by versions whose glyphs do not fade but simply switch on
    "brightness_override": 0.0,
    "brightness_threshold": 0.0,
    "isolate_cursor": True,
    "cursor_colour": hsl(0.242, 1, 0.73),
    "cursor_intensity": 2.0,
    "glyph_height_to_width": 1.0,
    "glyph_edge_crop": 0.0,
    "palette": GREEN_PALETTE,
    #: Vertical bands of colour that replace the palette, or None
    "stripes": None,
    #: The debug view, which colours cells by what the raindrop pass computed
    #: rather than by a palette
    "debug": False,
    #: Whether the variant is switched on for a fresh install
    "enabled": True,
    #: Raises the brightness to stand in for the effects this port leaves out.
    #: Only for variants that lean on one of them to light the screen up at
    #: all; everything else is drawn at the brightness the shader computes.
    "lift": 1.0,
}


class Version(object):
    """One variant of the rain, as a set of drawing parameters."""

    def __init__(self, name, label_id, **overrides):
        self.__dict__.update(DEFAULTS)
        self.__dict__.update(overrides)
        self.name = name
        self.label_id = label_id
        #: The toggle in settings.xml that switches this variant on and off
        self.setting_id = "enable-{}".format(name)

    @property
    def atlas(self):
        return FONTS[self.font]


#: The variants. The label ids are the ones this addon already used for the
#: scenes of the same name.
_VERSIONS = (
    Version("classic", 32062),
    Version(
        "megacity", 32065,
        font="megacity",
        animation_speed=0.5,
        columns=40,
    ),
    Version(
        # Drops the thunder and the slanted grid. The thunder is what lights
        # this one up -- it multiplies the brightness by up to eleven -- so
        # without it the variant is lifted instead of left nearly black.
        "nightmare", 32067,
        lift=2.2,
        font="gothic",
        isolate_cursor=False,
        base_brightness=-0.8,
        fall_speed=1.2,
        columns=60,
        raindrop_length=0.5,
        palette=(
            (0.0, hsl(0.0, 1.0, 0.0)),
            (0.2, hsl(0.0, 1.0, 0.2)),
            (0.4, hsl(0.0, 1.0, 0.4)),
            (0.7, hsl(0.1, 1.0, 0.7)),
            (1.0, hsl(0.2, 1.0, 1.0)),
        ),
    ),
    Version(
        # Drops the ripples
        "operator", 32068,
        cursor_colour=hsl(0.375, 1, 0.66),
        cursor_intensity=3.0,
        brightness_override=0.22,
        fall_speed=0.6,
        glyph_edge_crop=0.15,
        glyph_height_to_width=1.35,
        columns=108,
        raindrop_length=1.5,
        palette=(
            (0.0, hsl(0.4, 0.8, 0.0)),
            (0.5, hsl(0.4, 0.8, 0.5)),
            (1.0, hsl(0.4, 0.8, 1.0)),
        ),
    ),
    Version(
        # Drops the slanted grid
        "palimpsest", 32069,
        font="huberfishA",
        isolate_cursor=False,
        columns=40,
        raindrop_length=1.2,
        fall_speed=0.5,
        palette=(
            (0.0, hsl(0.15, 0.25, 0.9)),
            (0.4, hsl(0.6, 0.8, 0.1)),
        ),
    ),
    Version(
        # Drops the curved grid and the ripples. Its bloom carries a good
        # part of the brightness, and that is not ported either.
        "paradise", 32070,
        lift=1.5,
        font="coptic",
        isolate_cursor=False,
        base_brightness=-1.3,
        base_contrast=2.0,
        fall_speed=0.02,
        columns=40,
        raindrop_length=0.4,
        palette=(
            (0.0, hsl(0.0, 0.0, 0.0)),
            (0.3, hsl(0.0, 0.8, 0.3)),
            (0.5, hsl(0.1, 0.8, 0.5)),
            (0.6, hsl(0.1, 1.0, 0.6)),
            (0.9, hsl(0.1, 1.0, 0.9)),
        ),
    ),
    Version(
        # The classic rain, coloured by vertical stripes instead of a palette
        "rainbow", 32071,
        stripes=PRIDE_STRIPES,
    ),
    Version(
        "resurrections", 32072,
        font="resurrections",
        glyph_edge_crop=0.1,
        cursor_colour=hsl(0.292, 1, 0.8),
        base_brightness=-0.7,
        base_contrast=1.17,
        columns=70,
        palette=(
            (0.0, hsl(0.375, 0.9, 0.0)),
            (0.92, hsl(0.375, 1.0, 0.6)),
            (1.0, hsl(0.375, 1.0, 1.0)),
        ),
    ),
    Version(
        # Drops the perspective and the glint on its glyphs
        "trinity", 32073,
        font="resurrections",
        glyph_edge_crop=0.1,
        cursor_colour=hsl(0.292, 1, 0.8),
        base_brightness=-0.4,
        base_contrast=1.5,
        columns=60,
        raindrop_length=0.3,
        palette=(
            (0.0, hsl(0.37, 0.6, 0.0)),
            (1.0, hsl(0.37, 0.6, 0.5)),
        ),
    ),
    Version(
        # Drops the perspective and the glint on its glyphs
        "morpheus", 32066,
        font="resurrections",
        glyph_edge_crop=0.1,
        cursor_colour=hsl(0.333, 1, 0.85),
        base_brightness=-0.3,
        base_contrast=1.5,
        columns=60,
        raindrop_length=0.4,
        palette=(
            (0.0, hsl(0.97, 0.6, 0.0)),
            (1.0, hsl(0.97, 0.6, 0.5)),
        ),
    ),
    Version(
        # Drops the perspective and the glint on its glyphs
        "bugs", 32061,
        font="resurrections",
        glyph_edge_crop=0.1,
        cursor_colour=hsl(0.619, 1, 0.65),
        base_brightness=-0.3,
        base_contrast=1.5,
        columns=60,
        raindrop_length=0.3,
        palette=(
            (0.0, hsl(0.12, 0.6, 0.0)),
            (1.0, hsl(0.14, 0.6, 0.5)),
        ),
    ),
    Version(
        # The view the project uses to show what its raindrop pass computed:
        # red for the cursors, and the brightness split across two channels.
        # Switched off by default -- it is a tool, not a scene.
        "debug", 32064,
        debug=True,
        enabled=False,
    ),
    Version(
        "twilight", 32074,
        font="huberfishD",
        cursor_colour=hsl(0.167, 1, 0.8),
        cursor_intensity=1.5,
        columns=50,
        raindrop_length=0.9,
        fall_speed=0.1,
        palette=(
            (0.0, hsl(0.6, 1.0, 0.05)),
            (0.1, hsl(0.6, 0.8, 0.1)),
            (0.5, hsl(0.88, 0.8, 0.5)),
            (0.8, hsl(0.15, 1.0, 0.6)),
        ),
    ),
)

#: Listed by name, which is the order the settings show them in
VERSIONS = tuple(sorted(_VERSIONS, key=lambda version: version.name))

VERSIONS_BY_NAME = {version.name: version for version in VERSIONS}

#: Shown when the user has switched every variant off
DEFAULT_VERSION = VERSIONS_BY_NAME["classic"]
