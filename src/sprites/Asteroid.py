
import pygame, os

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Asteroid:
    x: float
    y: float
    w: int
    h: int
    vx: float
    vy: float
    image_path: Optional[str] = None
    _img: Optional[object] = field(default=None, init=False, repr=False)

    def __post_init__(self):
        if self.image_path is None:
            module_dir = os.path.dirname(os.path.abspath(__file__))
            self.image_path = os.path.join(module_dir, "images", "asteroid.png")

    def rect(self):
        assert pygame is not None
        return pygame.Rect(int(self.x), int(self.y), int(self.w), int(self.h))

    def reset(self, world_w: int, world_h: int, *, direction: int = 1):
        """Center the ball and set vertical velocity to 0; caller sets vx."""
        self.x = world_w // 2 - self.w // 2
        self.y = world_h // 2 - self.h // 2
        self.vy = 0.0

    def draw(self, surface):
        assert pygame is not None
        if self._img is None:
            self._load_image()
        if self._img is None:
            return
        surface.blit(self._img, (int(self.x), int(self.y)))

    # ------------------------- Internal helpers -------------------------
    def _load_image(self):
        assert pygame is not None
        path = self.image_path
        if not path or not os.path.isfile(path):
            self._img = None
            return
        try:
            src = pygame.image.load(path).convert_alpha()
            iw, ih = src.get_width(), src.get_height()
            if iw <= 0 or ih <= 0 or self.w <= 0 or self.h <= 0:
                self._img = None
                return
            # Preserve aspect ratio and letterbox into (w,h)
            scale = min(self.w / iw, self.h / ih)
            new_w = max(1, int(round(iw * scale)))
            new_h = max(1, int(round(ih * scale)))
            scaled = pygame.transform.smoothscale(src, (new_w, new_h))

            canvas = pygame.Surface((int(self.w), int(self.h)), pygame.SRCALPHA)
            off_x = (int(self.w) - new_w) // 2
            off_y = (int(self.h) - new_h) // 2
            canvas.blit(scaled, (off_x, off_y))
            self._img = canvas
        except Exception:
            self._img = None
