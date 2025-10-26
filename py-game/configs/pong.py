from __future__ import annotations
import os

# Base resolution used to derive fractional sizes
BASE_WIDTH, BASE_HEIGHT = 960, 540

# Window scale in (0, 1]; multiply base resolution by this to get initial window size
WINDOW_SCALE = 1.0  # adjust between 0.1 and 1.0 as desired

# Frame rate
FPS = 75

# Size and speed scalers (all 0..1), expressed relative to BASE dimensions
# Ship is square; size relative to height. Values chosen to match previous pixels at base res.
SHIP_SIZE_FRAC = 92 / BASE_HEIGHT           # ~0.1704 of height
SHIP_MARGIN_FRAC = 30 / BASE_WIDTH          # ~0.03125 of width
SHIP_SPEED_FRAC = 420.0 / BASE_HEIGHT       # ~0.7778 of height per second

ASTEROID_SPEED_FRAC = 360.0 / BASE_HEIGHT   # ~0.6667 of height per second
ASTEROID_SIZE_FRAC = 50 / BASE_HEIGHT       # ~0.0926 of height
ASTEROID_SPEED_INCREMENT = 0.0              # per-hit increment (pixels/sec)
ASTEROID_MAX_ANGLE_DEG = 48

# Match rules
SCORE_TO_WIN = 7

# Colors
BG_COLOR = (12, 12, 16)
FG_COLOR = (235, 235, 245)
ACCENT = (80, 200, 120)

# Dome positioning (tweakable, 0..1)
# How far to place the dome outside the top oval horizontally (fraction of the top oval width)
DOME_OUTSIDE_OFFSET_FRAC = 0.0
# Vertical adjustment relative to the top oval center (fraction of the top oval height)
DOME_VERTICAL_OFFSET_FRAC = 0.0

# Ship collision box controls
# - mode "box": use full ship bounding box
# - mode "content": use the scaled sprite content area only
SHIP_COLLISION_MODE = "content"  # "box" or "content"
SHIP_COLLISION_INFLATE = 0        # inflate (+) or deflate (-) the collision rect (width and height)

# Only the "front" portion of the ship should be hittable so asteroids behind the ship
# don't interact with the collision box. Fraction of ship width to use as the front hitbox
# (0..1). For the left ship (facing right), this is the rightmost fraction; for the right
# ship (facing left), this is the leftmost fraction.
SHIP_FRONT_HITBOX_FRAC = 0.55

# Starfield background settings
STAR_DENSITY = 0.0006             # stars per pixel (world area). 0.0006 -> ~311 stars at 960x540
STAR_SIZE_MIN, STAR_SIZE_MAX = 1, 2  # pixel size range for stars

# Font override for Pong: set to a path (absolute or relative to py-game/) to use a specific font file.
# Example (Hercules): "fonts/HerculesPixelRegular/HerculesPixelFontRegular-ovAX0.otf"
# Leave as None or empty string to use the system default font.
FONT_PATH = "fonts/HerculesPixelRegular/HerculesPixelFontRegular-ovAX0.otf"
