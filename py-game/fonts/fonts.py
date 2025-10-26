from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

try:
    import pygame
except Exception:  # pragma: no cover
    pygame = None  # type: ignore


@dataclass
class GameFonts:
    small: object
    medium: object
    big: object
    path: Optional[str] = None  # selected custom font file path, if any


def _resolve_font_path(font_path: Optional[str]) -> Optional[str]:
    """If font_path is provided, return an absolute path if the file exists; else None.
    This function intentionally avoids scanning directories; games should supply the path via config.
    """
    if not font_path:
        return None
    # If already absolute
    if os.path.isabs(font_path) and os.path.isfile(font_path):
        return font_path
    # Treat relative paths as relative to the py-game directory (one level up from this file's folder)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidate = os.path.join(base_dir, font_path)
    if os.path.isfile(candidate):
        return candidate
    # Not found
    return None


def load_fonts(*, small: int = 28, medium: int = 40, big: int = 72, font_path: Optional[str] = None) -> GameFonts:
    """Load game fonts, preferring the bundled OldBlitz demo font.

    Falls back to a system monospace font when the custom font is not available.
    Returns a GameFonts container with small/medium/big font objects and the chosen path.
    """
    assert pygame is not None, "pygame must be available to load fonts"
    path = _resolve_font_path(font_path)
    if path is not None:
        try:
            return GameFonts(
                small=pygame.font.Font(path, small),
                medium=pygame.font.Font(path, medium),
                big=pygame.font.Font(path, big),
                path=path,
            )
        except Exception:
            # Fall through to system fonts
            pass
    # System fallback
    return GameFonts(
        small=pygame.font.SysFont("monospace", small),
        medium=pygame.font.SysFont("monospace", medium),
        big=pygame.font.SysFont("monospace", big),
        path=None,
    )
