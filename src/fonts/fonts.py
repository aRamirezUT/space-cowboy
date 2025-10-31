
import pygame
import os

from dataclasses import dataclass
from typing import Optional


@dataclass
class GameFonts:
    small: object
    medium: object
    big: object
    path: Optional[str] = None  # selected custom font file path, if any


class FontManager:
    """Centralized font management for all games."""
    
    # Standard font sizes used across all games
    SMALL_SIZE = 24
    MEDIUM_SIZE = 36
    BIG_SIZE = 56
    
    _instance = None
    _fonts = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._fonts is None:
            self._fonts = None
    
    @classmethod
    def initialize(cls, font_path: Optional[str] = None):
        """Initialize the font manager with a specific font path."""
        instance = cls()
        instance._fonts = load_fonts(
            small=cls.SMALL_SIZE,
            medium=cls.MEDIUM_SIZE, 
            big=cls.BIG_SIZE,
            font_path=font_path
        )
        return instance
    
    @property
    def fonts(self) -> GameFonts:
        """Get the loaded fonts."""
        if self._fonts is None:
            raise RuntimeError("FontManager not initialized. Call FontManager.initialize() first.")
        return self._fonts
    
    @property
    def small(self):
        """Get small font."""
        return self.fonts.small
    
    @property
    def medium(self):
        """Get medium font."""
        return self.fonts.medium
    
    @property
    def big(self):
        """Get big font."""
        return self.fonts.big


def _resolve_font_path(font_path: Optional[str]) -> Optional[str]:
    """If font_path is provided, return an absolute path if the file exists; else None.
    This function intentionally avoids scanning directories; Games should pass relative paths.
    """
    if not font_path:
        return None
    # Treat relative paths as relative to the src directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidate = os.path.join(base_dir, font_path)
    if not os.path.isfile(candidate):
        return None
    return candidate


def load_fonts(*, small: int = 28, medium: int = 40, big: int = 72, font_path: Optional[str] = None) -> GameFonts:
    """Load game fonts.

    Falls back to a system monospace font when the custom font is not available.
    Returns a GameFonts container with small/medium/big font objects and the chosen path.
    """
    path = _resolve_font_path(font_path)
    if not path:
        # System fallback
        return GameFonts(
            small=pygame.font.SysFont("monospace", small),
            medium=pygame.font.SysFont("monospace", medium),
            big=pygame.font.SysFont("monospace", big),
            path=None,
        )
    return GameFonts(
        small=pygame.font.Font(path, small),
        medium=pygame.font.Font(path, medium),
        big=pygame.font.Font(path, big),
        path=path,
    )
