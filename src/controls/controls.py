from __future__ import annotations

from typing import Tuple
from .exg import BLEServer
from .exg import EXGClient
import numpy as np

try:
    import pygame
except Exception:  # pragma: no cover - helpful runtime message is already in main
    # Let the main module surface a clear error; avoid crashing on import in headless contexts
    pygame = None  # type: ignore

USE_BLUETOOTH = False  # Set to True/False to toggle Bluetooth input globally

class Controls:
    """Reusable input helpers for games.

    Provides:
    - keyboard_dir_for_player1/2: map pressed keys to direction ints with a default-down behavior
        (-1 for up while key held; +1 otherwise)
    - input_binary(): merged per-frame binary inputs (0.0/1.0) with BLE priority using a threshold
    - poll_ble(): returns per-player normalized analog values in [0, 1] by averaging two BLE channels
      (override read_ble_channels() to provide real data)
    """

    # Default normalization range for BLE channel averages. Override per game if needed.
    EMG_RELAX: float = 0.0
    EMG_MAX: float = 2000.0
    # Threshold to consider BLE analog as a binary press
    BLE_BINARY_THRESHOLD: float = 0.5
    
    def __init__(self) -> None:
        self.server = BLEServer()
        self.server.start()
        self.client = EXGClient()
        
    def __del__(self) -> None:
        self.server.stop()
        self.server.join()

    @staticmethod
    def _clamp01(v: float) -> float:
        return 0.0 if v < 0.0 else 1.0 if v > 1.0 else v

    @staticmethod
    def keyboard_dir_for_player1(keys) -> int:
        """Default to moving down unless the Up key is held.

        Player 1 uses W for up. Down (S) is ignored because down is the default.
        Returns:
            -1 when W is held (move up), otherwise +1 (move down by default).
        """
        up = keys[pygame.K_w]
        return -1 if up else 1

    @staticmethod
    def keyboard_dir_for_player2(keys) -> int:
        """Default to moving down unless the Up key is held.

        Player 2 uses Up Arrow for up. Down Arrow is ignored because down is the default.
        Returns:
            -1 when Up Arrow is held (move up), otherwise +1 (move down by default).
        """
        up = keys[pygame.K_UP]
        return -1 if up else 1

    def get_data(self) -> Tuple[float, float]:
        """Get latest BLE channel averages for both players.

        Override this method to provide real data from BLE channels.
        Returns:
            Tuple of two floats representing normalized BLE values for Player 1 and Player 2.
        """
        ch1, ch2 = self.client.get_data()
        avg1 = float(np.mean(ch1)) if ch1 is not None else 0.0
        avg2 = float(np.mean(ch2)) if ch2 is not None else 0.0
        # Normalize to [0, 1]
        norm1 = self._clamp01((avg1 - self.P1_RELAX) / (self.P1_MAX - self.P1_RELAX))
        norm2 = self._clamp01((avg2 - self.P2_RELAX) / (self.P2_MAX - self.P2_RELAX))
        return norm1, norm2

    # ---------------------- Binary input helpers ----------------------
    @staticmethod
    def keyboard_binary_for_player1(keys) -> float:
        """Return 1.0 while Player 1 attack key is held; else 0.0.
        Default attack key: W
        """
        return 1.0 if keys[pygame.K_w] else 0.0

    @staticmethod
    def keyboard_binary_for_player2(keys) -> float:
        """Return 1.0 while Player 2 attack key is held; else 0.0.
        Default attack key: Up Arrow
        """
        return 1.0 if keys[pygame.K_UP] else 0.0

    def input_binary(self) -> Tuple[float, float]:
        """Merged binary inputs with BLE priority.
        Returns floats in {0.0, 1.0} per player.
        BLE analog values are thresholded using BLE_BINARY_THRESHOLD.
        """
        assert pygame is not None, "pygame must be available to read input"
        keys = pygame.key.get_pressed()
        kb1 = self.keyboard_binary_for_player1(keys)
        kb2 = self.keyboard_binary_for_player2(keys)
        # Interpret BLE normalized values using a threshold
        return kb1, kb2
