
import pygame, os

from dataclasses import dataclass
from typing import Optional


@dataclass
class GameFonts:
    small: object
    medium: object
    big: object
    path: Optional[str] = None  # selected custom font file path, if any


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
