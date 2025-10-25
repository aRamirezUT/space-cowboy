from __future__ import annotations

from typing import Tuple

try:
    import pygame
except Exception:  # pragma: no cover - helpful runtime message is already in main
    # Let the main module surface a clear error; avoid crashing on import in headless contexts
    pygame = None  # type: ignore


class ControlsMixin:
    """Reusable input helpers for Pong.

    Provides:
    - keyboard_dir_for_player1/2: map pressed keys to direction ints (-1, 0, +1)
    - poll_ble: stub for BLE input collection for both players
    - input_dirs: merged per-frame directions prioritizing BLE when non-zero
    """

    @staticmethod
    def keyboard_dir_for_player1(keys) -> int:
        up = keys[pygame.K_w]
        down = keys[pygame.K_s]
        return (-1 if up and not down else 1 if down and not up else 0)

    @staticmethod
    def keyboard_dir_for_player2(keys) -> int:
        up = keys[pygame.K_UP]
        down = keys[pygame.K_DOWN]
        return (-1 if up and not down else 1 if down and not up else 0)

    @staticmethod
    def poll_ble() -> Tuple[int, int]:
        """
        TEMPLATE: Poll BLE input for both players.
        Return a tuple `(p1, p2)` where each value is:
          -1 => move up
           0 => no input
          +1 => move down

        Integration hints:
        - Use a non-blocking API or cached latest value to avoid frame stalls.
        - Translate your sensor/button state into {-1, 0, +1}.
        - Example with `bleak` (pseudo-code):
            # cache latest value in a module global via notification callback
            def notification_handler(sender, data):
                update_cached_directions_from(data)  # sets globals: p1_dir, p2_dir
            await client.start_notify(characteristic, notification_handler)
        """
        return 0, 0

    def input_dirs(self) -> Tuple[int, int]:
        assert pygame is not None, "pygame must be available to read input"
        keys = pygame.key.get_pressed()
        kb1 = self.keyboard_dir_for_player1(keys)
        kb2 = self.keyboard_dir_for_player2(keys)
        ble1, ble2 = self.poll_ble()

        # Prioritize BLE when non-zero; otherwise use keyboard
        d1 = ble1 if ble1 != 0 else kb1
        d2 = ble2 if ble2 != 0 else kb2
        return d1, d2
