
import pygame, random

from typing import Optional, Tuple

Color = Tuple[int, int, int]

def render_starfield_surface(
    width: int,
    height: int,
    *,
    density: float = 0.0006,
    size_min: int = 1,
    size_max: int = 2,
    bg_color: Color = (0, 0, 0),
    color_lo: int = 200,
    color_hi: int = 255,
) -> Optional[object]:
    """Generate a starfield surface of given size.

    Args:
        width, height: Pixel dimensions of the target surface.
        density: Approximate stars per pixel (width*height*density ~= star count).
        size_min, size_max: Inclusive pixel size range for each star.
        bg_color: Background color. Defaults to black.
        color_lo, color_hi: Brightness range for stars (grayscale-ish, slight blue tint).

    Returns:
        A pygame Surface with the generated starfield, or None if pygame isn't available
        or parameters are invalid.
    """
    
    if width <= 0 or height <= 0:
        return None
    if size_min <= 0 or size_max < size_min:
        return None

    r = random

    try:
        canvas = pygame.Surface((width, height))
        canvas.fill(bg_color)

        total_pixels = width * height
        count = max(1, int(total_pixels * max(0.0, density)))

        # Clamp brightness range
        lo = max(0, min(255, color_lo))
        hi = max(lo, min(255, color_hi))

        for _ in range(count):
            x = r.randint(0, width - 1)
            y = r.randint(0, height - 1)
            size = r.randint(size_min, size_max)
            val = r.randint(lo, hi)
            color = (val, val, min(255, val + 10))
            pygame.draw.rect(canvas, color, pygame.Rect(x, y, size, size))

        return canvas
    except Exception:
        return None
