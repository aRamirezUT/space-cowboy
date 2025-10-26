# Font override: set to a path (absolute or relative to py-game/) to use a specific font file.
# Example (Hercules): "fonts/HerculesPixelRegular/HerculesPixelFontRegular-ovAX0.otf"
# Example (OldBlitz): "fonts/oldblitz-font/OldbitzDemo-BLl98.otf"
# Leave as None to use system default.
FONT_PATH = "fonts/HerculesPixelRegular/HerculesPixelFontRegular-ovAX0.otf"

# Base resolution used to derive fractional sizes
BASE_WIDTH, BASE_HEIGHT = 960, 540
# Starfield background settings
STAR_DENSITY = 0.0006             # stars per pixel (world area). 0.0006 -> ~311 stars at 960x540
STAR_SIZE_MIN, STAR_SIZE_MAX = 1, 2  # pixel size range for stars