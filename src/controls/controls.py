from __future__ import annotations

from typing import Tuple
from .exg import BLEServer
from .exg import EXGClient
import numpy as np
import pygame

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
    
    def __init__(self) -> None:
        self.server = BLEServer()
        self.server.start()
        self.client = EXGClient()
        self.P1_RELAX = 0.0
        self.P1_FLEX = 1.0
        self.P2_RELAX = 0.0
        self.P2_FLEX = 1.0
        self.last_p1 = 0.0
        self.last_p2 = 0.0
        
    def __del__(self) -> None:
        self.server.stop()
        self.server.join()

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
        if ch1 is None or ch2 is None:
            return self.last_p1, self.last_p2
        avg1 = float(np.mean(ch1))
        avg2 = float(np.mean(ch2))
        p1_threshold = (self.P1_FLEX + self.P1_RELAX) / 2
        p2_threshold = (self.P2_FLEX + self.P2_RELAX) / 2
        avg1 = 1.0 if avg1 >= p1_threshold else 0.
        avg2 = 1.0 if avg2 >= p2_threshold else 0.
        self.last_p1 = avg1
        self.last_p2 = avg2
        return avg1, avg2

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
    
    def calibrate_relax(self) -> None:
        """Calibrate EMG relax levels for both players."""
        # Grab last 3 seconds of data
        ch1, ch2 = self.client.get_data(seconds=3.0)
        if ch1 is not None and len(ch1) > 0:
            self.P1_RELAX = float(np.mean(ch1))
        if ch2 is not None and len(ch2) > 0:
            self.P2_RELAX = float(np.mean(ch2))
            
    def calibrate_flex(self) -> None:
        """Calibrate EMG flex levels for both players."""
        ch1, ch2 = self.client.get_data(seconds=3.0)
        if ch1 is not None and len(ch1) > 0:
            self.P1_FLEX = float(np.mean(ch1))
        if ch2 is not None and len(ch2) > 0:
            self.P2_FLEX = float(np.mean(ch2))
    
    def input_binary(self) -> Tuple[float, float]:
        """Merged binary inputs with BLE priority.
        Returns floats in {0.0, 1.0} per player.
        BLE analog values are thresholded using BLE_BINARY_THRESHOLD.
        """
        return self.get_data()