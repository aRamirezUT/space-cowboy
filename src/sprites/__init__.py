"""Sprite classes and helpers for MYO BEBOP Pong.

Exposes core sprites and background helpers so games can import from `sprites`.
"""

from .ship import Ship
from .ball import Ball
from .background import make_starfield_surface

__all__ = ["Ship", "Ball", "make_starfield_surface"]
