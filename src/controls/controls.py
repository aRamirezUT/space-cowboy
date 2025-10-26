from __future__ import annotations

from typing import Tuple

try:
    import pygame
except Exception:  # pragma: no cover - helpful runtime message is already in main
    # Let the main module surface a clear error; avoid crashing on import in headless contexts
    pygame = None  # type: ignore

USE_BLUETOOTH = False  # Set to True/False to toggle Bluetooth input globally

class ControlsMixin:
    """Reusable input helpers for games.

    Provides:
    - keyboard_dir_for_player1/2: map pressed keys to direction ints with a default-down behavior
        (-1 for up while key held; +1 otherwise)
    - input_dirs(): merged per-frame directions prioritizing BLE when non-zero
    - input_binary(): merged per-frame binary inputs (0.0/1.0) with BLE priority using a threshold
    - poll_ble(): returns per-player normalized analog values in [0, 1] by averaging two BLE channels
      (override read_ble_channels() to provide real data)
    """

    # Default normalization range for BLE channel averages. Override per game if needed.
    BLE_MIN: float = 0.0
    BLE_MAX: float = 2000.0
    # Threshold to consider BLE analog as a binary press
    BLE_BINARY_THRESHOLD: float = 0.5

    @staticmethod
    def _clamp01(v: float) -> float:
        return 0.0 if v < 0.0 else 1.0 if v > 1.0 else v

    def read_ble_channels(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """
        Read two BLE channels per device, if a provider is attached.

        Returns a tuple of two devices, each as (ch1, ch2) floats:
            ((p1_ch1, p1_ch2), (p2_ch1, p2_ch2))
        
        Expects an optional attribute `ble_provider` on `self` implementing one of:
          - read_channels() -> ((p1_ch1, p1_ch2), (p2_ch1, p2_ch2))
          - read_ble_channels() -> same as above
          - get_data() -> (p1_array, p2_array)  # last samples used

        If no provider is present or an error occurs, returns zeros.
        """
        prov = getattr(self, "ble_provider", None)
        if prov is not None:
            try:
                if hasattr(prov, "read_channels") and callable(prov.read_channels):
                    return prov.read_channels()
                if hasattr(prov, "read_ble_channels") and callable(prov.read_ble_channels):
                    return prov.read_ble_channels()
                if hasattr(prov, "get_data") and callable(prov.get_data):
                    # Support EXGClient interface: returns (p1_array, p2_array)
                    p1_arr, p2_arr = prov.get_data()
                    # Use last sample when available; otherwise 0.0
                    def last_or_zero(arr) -> float:
                        try:
                            if arr is None:
                                return 0.0
                            # numpy-like arrays
                            if hasattr(arr, "__len__") and len(arr) > 0:
                                return float(arr[-1])
                            return float(arr)
                        except Exception:
                            return 0.0
                    v1 = last_or_zero(p1_arr)
                    v2 = last_or_zero(p2_arr)
                    # Duplicate each value into two channels per device so poll_ble's
                    # averaging path remains valid.
                    return (v1, v1), (v2, v2)
            except Exception:
                pass
        return (0.0, 0.0), (0.0, 0.0)

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

    def poll_ble(self) -> Tuple[float, float]:
        """Poll two BLE channels per device, average and normalize to [0, 1].

        Returns a tuple `(p1, p2)` of floats in [0.0, 1.0], one per player.
        Implement `read_ble_channels()` in your game to provide real (ch1, ch2)
        readings per device. The two channels are averaged and linearly scaled
        using BLE_MIN..BLE_MAX, then clamped to [0, 1].

        Note: Directional games like Pong expect -1/0/+1 semantics and should
        override this method (or use a separate directional BLE reader). The
        default implementation is intended for binary/analog pressure inputs.
        """
        (p1c1, p1c2), (p2c1, p2c2) = (0.0, 0.0), (0.0, 0.0)
        try:
            (p1c1, p1c2), (p2c1, p2c2) = self.read_ble_channels()
        except Exception:
            # Keep defaults if BLE is unavailable or raises
            pass
        avg1 = (float(p1c1) + float(p1c2)) / 2.0
        avg2 = (float(p2c1) + float(p2c2)) / 2.0
        denom = max(1e-9, float(self.BLE_MAX) - float(self.BLE_MIN))
        n1 = self._clamp01((avg1 - float(self.BLE_MIN)) / denom)
        n2 = self._clamp01((avg2 - float(self.BLE_MIN)) / denom)
        return n1, n2

    def input_dirs(self) -> Tuple[int, int]:
        assert pygame is not None, "pygame must be available to read input"
        keys = pygame.key.get_pressed()
        kb1 = self.keyboard_dir_for_player1(keys)
        kb2 = self.keyboard_dir_for_player2(keys)
        ble1, ble2 = self.poll_ble()

        # Only allow BLE to override keyboard for directional games when it
        # explicitly encodes direction as -1/0/+1 integers. Otherwise, fall
        # back to keyboard (since normalized BLE [0,1] lacks direction).
        d1 = kb1
        d2 = kb2
        if isinstance(ble1, int) and ble1 != 0:
            d1 = -1 if ble1 < 0 else 1
        if isinstance(ble2, int) and ble2 != 0:
            d2 = -1 if ble2 < 0 else 1
        return d1, d2

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
        b1, b2 = self.poll_ble()
        # Interpret BLE normalized values using a threshold
        ble1 = 1.0 if float(b1) >= float(self.BLE_BINARY_THRESHOLD) else 0.0
        ble2 = 1.0 if float(b2) >= float(self.BLE_BINARY_THRESHOLD) else 0.0
        v1 = ble1 if USE_BLUETOOTH else kb1
        v2 = ble2 if USE_BLUETOOTH else kb2
        return v1, v2
