from __future__ import annotations

# Base resolution used to derive fractional sizes
BASE_WIDTH, BASE_HEIGHT = 960, 540

# Window scale and fullscreen default
WINDOW_SCALE = 1.0
FULLSCREEN_DEFAULT = True

# Frame rate
FPS = 75

# Colors
BG_COLOR = (12, 12, 16)
FG_COLOR = (235, 235, 245)
ACCENT = (80, 200, 120)
ALERT = (230, 70, 70)
WARNING = (240, 210, 80)

# Mechanics
ATTACK_THRESHOLD = 0.10  # input > threshold means attack; otherwise block
SHIELD_MAX_SECONDS = 3.0  # total blocking time available per round

# Sprites (cowboy blaster/shield) sizing and placement
# Height of each cowboy relative to screen height
SHIP_HEIGHT_FRAC = 0.46
# Approximate aspect scale used to pick a reasonable bounding width from height
SHIP_ASPECT_SCALE = 0.70
# Horizontal margin from edges as a fraction of screen width
SHIP_MARGIN_FRAC = 0.12
# Ground line placement and foot gap
GROUND_FRAC = 0.92
FOOT_MARGIN_PX = 8

# Gauges
INPUT_BAR_WIDTH_FRAC = 0.30  # fraction of width for input bar per player
INPUT_BAR_HEIGHT = 18
SHIELD_BAR_HEIGHT = 10
GAUGE_MARGIN_PX = 12

# Text rendering (outline)
TEXT_OUTLINE_PX = 2
TEXT_OUTLINE_COLOR = (0, 0, 0)

# Font override: set to a path (absolute or relative to py-game/) to use a specific font file.
# Example: "fonts/HerculesPixelRegular/HerculesPixelFontRegular-ovAX0.otf"
FONT_PATH = "fonts/HerculesPixelRegular/HerculesPixelFontRegular-ovAX0.otf"

# Starfield background fallback
STAR_DENSITY = 0.0006
STAR_SIZE_MIN, STAR_SIZE_MAX = 1, 2
