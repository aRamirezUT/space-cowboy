# Base resolution used to derive fractional sizes
BASE_WIDTH, BASE_HEIGHT = 960, 540

# Window scale in (0, 1]; multiply base resolution by this to get initial window size
WINDOW_SCALE = 1.0

# Start the game fullscreen by default. If False, uses WINDOW_SCALE for initial size.
FULLSCREEN_DEFAULT = True

# Frame rate
FPS = 75

# Colors
BG_COLOR = (12, 12, 16)
FG_COLOR = (235, 235, 245)
ACCENT = (80, 200, 120)

# Player sprite sizing and placement (fractions relative to BASE dimensions)
# Height of each cowboy relative to screen height
SHIP_HEIGHT_FRAC = 0.48
# Horizontal size derived from height via aspect scale (tune as needed)
SHIP_ASPECT_SCALE = 0.70
# Horizontal margin from edges as a fraction of screen width
SHIP_MARGIN_FRAC = 0.1

# Vertical placement
# Y position of the ground line as a fraction of total height (0.0 top .. 1.0 bottom)
# Push this closer to 1.0 to place players nearer the bottom.
GROUND_FRAC = 1.0
# Gap in pixels between player feet and the ground line
FOOT_MARGIN_PX = 8

# Fallback starfield background settings (used if western background image is missing)
STAR_DENSITY = 0.0006
STAR_SIZE_MIN, STAR_SIZE_MAX = 1, 2

# Text rendering
# Outline thickness (in pixels) for overlay texts and player labels
TEXT_OUTLINE_PX = 2
# Outline color for text borders
TEXT_OUTLINE_COLOR = (0, 0, 0)

# Font override: set to a path (absolute or relative to py-game/) to use a specific font file.
# Example (Hercules): "fonts/HerculesPixelRegular/HerculesPixelFontRegular-ovAX0.otf"
# Example (OldBlitz): "fonts/oldblitz-font/OldbitzDemo-BLl98.otf"
# Leave as None to use system default.
FONT_PATH = "fonts/HerculesPixelRegular/HerculesPixelFontRegular-ovAX0.otf"
