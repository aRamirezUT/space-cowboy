
import pygame
import os

from typing import Optional


class Player:
    def __init__(
        self, 
        x: float, 
        y: float, 
        w: float, 
        h: float, 
        world_height: float,
        image_name: str = "",
    ):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.world_height = world_height
        module_dir = os.path.dirname(os.path.abspath(__file__))
        self.image_path = os.path.join(module_dir, "images", image_name)
        
        # Cached images
        self._img_right: pygame.Surface = pygame.Surface((1, 1))
        self._img_left: pygame.Surface = pygame.Surface((1, 1))
        
        # Cached content placement within bounding box
        self._content_w: int = 0
        self._content_h: int = 0
        self._content_off_x: int = 0
        self._content_off_y: int = 0
    
    def rect(self) -> pygame.Rect:
        rx = int(self.x + self._content_off_x)
        ry = int(self.y + self._content_off_y)
        rw, rh = self._content_w or self.w, self._content_h or self.h
        r = pygame.Rect(rx, ry, rw, rh)

        return r

    def move(self, dy: float) -> None:
        self.y += dy
        # Clamp to world bounds using configured world height
        self.y = max(0, min(self.world_height - self.h, self.y))

    def change_sprite(self, image_name: str) -> None:
        """Change the player's sprite image and clear cached images."""
        module_dir = os.path.dirname(os.path.abspath(__file__))
        new_image_path = os.path.join(module_dir, "images", image_name)
        
        if os.path.isfile(new_image_path):
            self.image_path = new_image_path

    def get_image(self, facing_right: bool) -> pygame.Surface:
        """Get the appropriate image for the player, ensuring images are loaded."""
        if not self._ensure_images():
            raise RuntimeError("Player image not available.")
        return self._img_right if facing_right else self._img_left

    def draw(self, surface: pygame.Surface, facing_right: bool) -> None:
        # Draw the sprite image only; no custom vector fallback
        self._ensure_images()
        img = self._img_right if facing_right else self._img_left
        if img is None:
            raise RuntimeError("Player image not available for drawing.")
        surface.blit(img, (int(self.x), int(self.y)))

    # ------------------------- Internal helpers -------------------------
    def _ensure_images(self) -> bool:
        """Load and cache scaled images for right/left if possible."""
        path = self.image_path
        if not path or not os.path.isfile(path):
            raise RuntimeError(f"Player image path not provided/invalid: {path}")
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
        except Exception as e:
            raise RuntimeError(f"Failed to load or process player image: {e}")