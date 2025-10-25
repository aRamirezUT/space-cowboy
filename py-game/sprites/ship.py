from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

try:
    import pygame
except Exception:
    pygame = None  # type: ignore


@dataclass
class Ship:
    x: int
    y: int
    w: int
    h: int
    world_height: int
    image_path: Optional[str] = None
    _img_right: Optional[object] = field(default=None, init=False, repr=False)
    _img_left: Optional[object] = field(default=None, init=False, repr=False)
    # Collision tuning: "box" uses full w×h; "content" uses the scaled image area only
    collision_mode: str = "content"  # "box" | "content"
    collision_inflate: int = 0    # total pixels to inflate (+) or deflate (-) rect in both width and height
    # Cached content placement within bounding box
    _content_w: int = field(default=0, init=False, repr=False)
    _content_h: int = field(default=0, init=False, repr=False)
    _content_off_x: int = field(default=0, init=False, repr=False)
    _content_off_y: int = field(default=0, init=False, repr=False)

    def __post_init__(self):
        # Default to bundled sprite if no image provided
        if self.image_path is None:
            module_dir = os.path.dirname(os.path.abspath(__file__))
            self.image_path = os.path.join(module_dir, "images", "alien-saucer.png")

    def rect(self):
        assert pygame is not None
        if self.collision_mode == "content" and self._img_right is not None:
            rx = int(self.x + self._content_off_x)
            ry = int(self.y + self._content_off_y)
            rw, rh = self._content_w or self.w, self._content_h or self.h
            r = pygame.Rect(rx, ry, rw, rh)
        else:
            r = pygame.Rect(int(self.x), int(self.y), self.w, self.h)
        if self.collision_inflate != 0:
            # pygame.Rect.inflate expects deltas to add to width/height (not per side)
            r = r.inflate(self.collision_inflate, self.collision_inflate)
        return r

    def move(self, dy: float):
        self.y += dy
        # Clamp to world bounds using configured world height
        self.y = max(0, min(self.world_height - self.h, self.y))

    def draw(self, surface, *, facing_right: bool, fg_color, accent,
             dome_outside_offset_frac: float = 0.0,
             dome_vertical_offset_frac: float = 0.0):
        assert pygame is not None

        # Draw the sprite image only; no custom vector fallback
        if not self._ensure_images():
            return  # Image not available; draw nothing

        img = self._img_right if facing_right else self._img_left
        if img is None:
            return
        surface.blit(img, (int(self.x), int(self.y)))

    # ------------------------- Internal helpers -------------------------
    def _ensure_images(self) -> bool:
        """Load and cache scaled images for right/left if possible.
        Returns True if an image is ready for drawing.
        """
        if self._img_right is not None and self._img_left is not None:
            return True

        path = self.image_path
        if not path or not os.path.isfile(path):
            return False
        try:
            # Load source image
            src = pygame.image.load(path).convert_alpha()
            iw, ih = src.get_width(), src.get_height()

            # Preserve aspect ratio: fit within (w,h) and letterbox
            target_w, target_h = int(self.w), int(self.h)
            if iw == 0 or ih == 0 or target_w <= 0 or target_h <= 0:
                return False
            scale = min(target_w / iw, target_h / ih)
            new_w = max(1, int(round(iw * scale)))
            new_h = max(1, int(round(ih * scale)))
            scaled = pygame.transform.smoothscale(src, (new_w, new_h))

            # Composite onto a transparent canvas centered within the bounding box
            canvas = pygame.Surface((target_w, target_h), pygame.SRCALPHA)
            off_x = (target_w - new_w) // 2
            off_y = (target_h - new_h) // 2
            canvas.blit(scaled, (off_x, off_y))

            # Cache content placement for collision calculations when using "content"
            self._content_w, self._content_h = new_w, new_h
            self._content_off_x, self._content_off_y = off_x, off_y

            self._img_right = canvas
            self._img_left = pygame.transform.flip(canvas, True, False)
            return True
        except Exception:
            # Image may not exist or be invalid; stick with vector
            self._img_right = None
            self._img_left = None
            return False