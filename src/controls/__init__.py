"""Controls package for input handling (keyboard + BLE stubs).

Exports:
- ControlsMixin: mixin providing input direction helpers for both players and BLE hook.
"""

from .controls import ControlsMixin

__all__ = ["ControlsMixin"]
