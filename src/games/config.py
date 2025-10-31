# Font override: set to a path (absolute or relative to py-game/) to use a specific font file.
# Example (Hercules): "fonts/HerculesPixelRegular/HerculesPixelFontRegular-ovAX0.otf"
# Example (OldBlitz): "fonts/oldblitz-font/OldbitzDemo-BLl98.otf"
# Leave as None to use system default.
FONT_PATH = "fonts/HerculesPixelRegular/HerculesPixelFontRegular-ovAX0.otf"

# Sprite paths (relative to project root)
SPRITES_DIR = "src/sprites/images"

# Sprite filenames for different games
SPRITE_PATHS = {
    # Quickdraw game sprites
    "quickdraw": {
        "left_holstered": "space-cowboy-holstered-east-facing.png",
        "right_holstered": "space-cowboy-holstered-west-facing.png", 
        "left_drawn": "space-cowboy-drawn-east-facing.png",
        "right_drawn": "space-cowboy-drawn-west-facing.png",
        "background": "western-background.png"
    },
    # Twin Suns Duel sprites
    "twin_suns": {
        "left_shield": "cowboy-shield-east.png",
        "right_shield": "cowboy-shield-west.png",
        "left_blaster": "cowboy-blaster-east.png", 
        "right_blaster": "cowboy-blaster-west.png"
    },
    # Common sprites
    "common": {
        "asteroid": "asteroid.png",
        "alien_saucer": "alien-saucer.png",
        "alien_cowboy": "alien-space-cowboy.png"
    }
}

# Base resolution used to derive fractional sizes
BASE_WIDTH, BASE_HEIGHT = 960, 540
# Starfield background settings
STAR_DENSITY = 0.0006             # stars per pixel (world area). 0.0006 -> ~311 stars at 960x540
STAR_SIZE_MIN, STAR_SIZE_MAX = 1, 2  # pixel size range for stars