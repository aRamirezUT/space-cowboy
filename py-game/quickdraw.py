#!/usr/bin/python3
"""
Western Quickdraw Duel using existing py-game helpers.

Rules
- Press SPACE/ENTER to arm the duel and start a 3-second countdown.
- After "DRAW!", the first player to input wins.
  - Keyboard: Player 1 uses W; Player 2 uses Up Arrow.
  - BLE: If you wire in poll_ble() to return non-zero when a player "draws",
    that player wins. Only transitions from 0->non-zero after DRAW count.
- Press R to restart, Q or ESC to quit, F11 to toggle fullscreen.

Run
  python3 py-game/quickdraw.py

Sprite
- Both players use `sprites/images/western-cowboy.png`
- The winner gets a simple pulsing scale animation as a template for further work.

If pygame is missing, install it: pip install pygame
"""

from __future__ import annotations

import math
import os
import sys
from typing import Optional, Tuple

try:
    import pygame
except Exception as e:  # pragma: no cover - runtime check for friendly error
    print("pygame is required to run this game.\nInstall with: pip install pygame", file=sys.stderr)
    raise

# Reuse Pong's config for sizes, colors, and FPS
from configs.pong import (
    BASE_WIDTH, BASE_HEIGHT, WINDOW_SCALE,
    FPS,
    BG_COLOR, FG_COLOR, ACCENT,
    STAR_DENSITY, STAR_SIZE_MIN, STAR_SIZE_MAX,
)

# Logical world size (fixed) and initial display size
WIDTH, HEIGHT = BASE_WIDTH, BASE_HEIGHT
INITIAL_DISPLAY_SIZE = (int(BASE_WIDTH * WINDOW_SCALE), int(BASE_HEIGHT * WINDOW_SCALE))

# Ship sizing and placement
SHIP_H_FRAC = 0.48   # each cowboy sprite is about half screen height
SHIP_W = int(HEIGHT * SHIP_H_FRAC * 0.70)  # width scales with sprite aspect; tuned
SHIP_H = int(HEIGHT * SHIP_H_FRAC)
MARGIN_X = int(WIDTH * 0.12)

from controls import ControlsMixin
from sprites import Ship
from sprites.background import make_starfield_surface


class QuickdrawGame(ControlsMixin):
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Space Cowboy Quickdraw")
        # Start fullscreen like Pong
        self.screen = pygame.display.set_mode((0, 0), pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.FULLSCREEN)
        self.fullscreen = True
        self.scene = pygame.Surface((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 28)
        self.big_font = pygame.font.SysFont("monospace", 72)
        self.med_font = pygame.font.SysFont("monospace", 40)

        self._bg_prepared = None
        self._prepare_background()

        # Assets
        spr_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sprites", "images")
        cowboy = os.path.join(spr_dir, "western-cowboy.png")

        # Place cowboys
        center_y = HEIGHT // 2
        self.left = Ship(MARGIN_X, center_y - SHIP_H // 2, SHIP_W, SHIP_H, HEIGHT, image_path=cowboy)
        self.right = Ship(WIDTH - MARGIN_X - SHIP_W, center_y - SHIP_H // 2, SHIP_W, SHIP_H, HEIGHT, image_path=cowboy)

        # State machine
        self.running = True
        self.waiting_for_start = True
        self.countdown_start_ms = None
        self.countdown_total = 3000  # ms
        self.draw_signal_ms = None  # when "DRAW!" appeared
        self.draw_enabled = False
        self.winner = None  # 0 left, 1 right
        self.foul_by = None  # player index who drew too soon

        # Input edge detection for BLE
        self._ble_prev = (0, 0)

        # Winner animation timing
        self.win_anim_start_ms = None
        self.win_anim_duration = 1400  # ms

    # --------------------------- Main loop --------------------------------
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            now = pygame.time.get_ticks()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    if not getattr(self, 'fullscreen', False):
                        self.screen = pygame.display.set_mode(event.size, pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        self.running = False
                    elif event.key == pygame.K_r:
                        self._restart()
                    elif event.key == pygame.K_F11:
                        if getattr(self, 'fullscreen', False):
                            self.screen = pygame.display.set_mode(INITIAL_DISPLAY_SIZE, pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)
                            self.fullscreen = False
                        else:
                            self.screen = pygame.display.set_mode((0, 0), pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.FULLSCREEN)
                            self.fullscreen = True
                    elif self.waiting_for_start and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        self._arm_countdown()
                    else:
                        self._maybe_handle_draw_key(event)

            # Poll BLE each frame for 0->nonzero transitions after DRAW is enabled
            self._maybe_handle_draw_ble()

            self._update_state(now)
            self._draw(now)

        pygame.quit()

    # --------------------------- State & Input ----------------------------
    def _arm_countdown(self):
        self.waiting_for_start = False
        self.winner = None
        self.foul_by = None
        self.countdown_start_ms = pygame.time.get_ticks()
        self.draw_signal_ms = None
        self.draw_enabled = False
        self._ble_prev = (0, 0)
        self.win_anim_start_ms = None

    def _restart(self):
        self.waiting_for_start = True
        self.winner = None
        self.foul_by = None
        self.countdown_start_ms = None
        self.draw_signal_ms = None
        self.draw_enabled = False
        self._ble_prev = (0, 0)
        self.win_anim_start_ms = None
        # recenters
        self.left.y = HEIGHT // 2 - SHIP_H // 2
        self.right.y = HEIGHT // 2 - SHIP_H // 2
        self._prepare_background()

    def _maybe_handle_draw_key(self, event):
        # Handle both early foul (before DRAW) and valid draw (after DRAW)
        if self.winner is not None:
            return
        if event.type != pygame.KEYDOWN:
            return
        p: Optional[int] = None
        if event.key == pygame.K_w:
            p = 0
        elif event.key == pygame.K_UP:
            p = 1
        if p is None:
            return
        if not self.waiting_for_start and not self.draw_enabled:
            # Foul: drew too soon
            self._declare_foul(p)
        elif self.draw_enabled:
            # Valid draw
            self._declare_winner(p)

    def _maybe_handle_draw_ble(self):
        # Check for 0->nonzero edges to detect draw presses for both early foul and valid draw
        if self.winner is not None:
            return
        try:
            b1, b2 = self.poll_ble()
        except Exception:
            b1, b2 = 0, 0
        p1_prev, p2_prev = self._ble_prev
        # Edge triggers
        if b1 != 0 and p1_prev == 0:
            if not self.waiting_for_start and not self.draw_enabled:
                self._declare_foul(0)
            elif self.draw_enabled:
                self._declare_winner(0)
        elif b2 != 0 and p2_prev == 0:
            if not self.waiting_for_start and not self.draw_enabled:
                self._declare_foul(1)
            elif self.draw_enabled:
                self._declare_winner(1)
        self._ble_prev = (b1, b2)

    def _declare_winner(self, who: int):
        if self.winner is None:
            self.winner = who
            self.win_anim_start_ms = pygame.time.get_ticks()

    def _declare_foul(self, who: int):
        # A player drew before DRAW: they lose, the other wins.
        if self.winner is not None:
            return
        self.foul_by = who
        self._declare_winner(1 - who)

    def _update_state(self, now_ms: int):
        if self.waiting_for_start:
            return
        # Handle countdown and enabling draw
        if not self.draw_enabled:
            if self.countdown_start_ms is None:
                return
            elapsed = now_ms - self.countdown_start_ms
            if elapsed >= self.countdown_total:
                # Start DRAW phase
                self.draw_enabled = True
                self.draw_signal_ms = now_ms
        # Winner animation expiry handled in draw; no movement in this game

    # --------------------------- Rendering --------------------------------
    def _draw(self, now_ms: int):
        if self._bg_prepared is not None:
            self.scene.blit(self._bg_prepared, (0, 0))
        else:
            self.scene.fill(BG_COLOR)

        # Optional ground line for style
        pygame.draw.line(self.scene, (64, 64, 76), (0, int(HEIGHT*0.8)), (WIDTH, int(HEIGHT*0.8)), 2)

        # Draw players (with winner animation)
        self._draw_player(self.left, facing_right=True, now_ms=now_ms, is_winner=(self.winner == 0))
        self._draw_player(self.right, facing_right=False, now_ms=now_ms, is_winner=(self.winner == 1))

        # UI overlays
        if self.waiting_for_start:
            self._overlay_center(self.big_font, "Quickdraw Duel", FG_COLOR, y=HEIGHT//2 - 80)
            self._overlay_center(self.font, "Press SPACE or ENTER to arm", FG_COLOR, y=HEIGHT//2 + 8)
        else:
            if not self.draw_enabled:
                # 3..2..1 countdown
                assert self.countdown_start_ms is not None
                remaining = max(0, self.countdown_total - (now_ms - self.countdown_start_ms))
                n = int(math.ceil(remaining / 1000.0))  # 3000..2001 => 3, 2000..1001 => 2, 1000..1 => 1, 0 => 0
                if n > 0:
                    self._overlay_center(self.big_font, str(n), ACCENT, y=HEIGHT//2 - 40)
                else:
                    # transient pre-DRAW frame; handled by enabling draw on next tick
                    pass
            else:
                # After enabling draw, show DRAW! for a short time if no winner yet
                if self.winner is None and self.draw_signal_ms is not None and (now_ms - self.draw_signal_ms) < 900:
                    self._overlay_center(self.med_font, "DRAW!", ACCENT, y=HEIGHT//2 - 60)

        if self.winner is not None:
            if self.foul_by is not None:
                # Show foul message prominently
                self._overlay_center(self.med_font, "Too soon, you lose!", (240, 120, 120), y=HEIGHT//2 - 160)
                msg = "Player 1 wins!" if self.winner == 0 else "Player 2 wins!"
            else:
                msg = "Player 1 drew first!" if self.winner == 0 else "Player 2 drew first!"
            self._overlay_center(self.med_font, msg, FG_COLOR, y=HEIGHT//2 - 120)
            self._overlay_center(self.font, "Press R to restart • Q to quit", FG_COLOR, y=HEIGHT//2 - 76)

        # Scale scene to display
        display_size = self.screen.get_size()
        scaled = pygame.transform.smoothscale(self.scene, display_size)
        self.screen.blit(scaled, (0, 0))
        pygame.display.flip()

    def _overlay_center(self, font, text: str, color, *, y: int):
        surf = font.render(text, True, color)
        self.scene.blit(surf, (WIDTH // 2 - surf.get_width() // 2, y))

    def _draw_player(self, ship: Ship, *, facing_right: bool, now_ms: int, is_winner: bool):
        # If animating winner, apply a simple pulsing scale effect to the sprite image
        if is_winner and self.win_anim_start_ms is not None:
            t = (now_ms - self.win_anim_start_ms) / 1000.0
            # Damped pulse: amplitude decays over ~1.4s
            amp = max(0.0, 0.16 * math.exp(-1.6 * t))
            pulse = math.sin(2.0 * math.pi * (2.2 * t))  # 2.2 Hz pulse
            scale = 1.0 + amp * pulse
            # Access cached image from Ship and scale it
            try:
                # Load images if needed
                ship._ensure_images()  # type: ignore[attr-defined]
                img = ship._img_right if facing_right else ship._img_left  # type: ignore[attr-defined]
            except Exception:
                img = None
            if img is not None:
                iw, ih = img.get_width(), img.get_height()
                new_w = max(1, int(round(iw * scale)))
                new_h = max(1, int(round(ih * scale)))
                scaled = pygame.transform.smoothscale(img, (new_w, new_h))
                # Center the scaled image within the ship's bounding box
                off_x = ship.x + (ship.w - new_w) // 2
                off_y = ship.y + (ship.h - new_h) // 2
                self.scene.blit(scaled, (int(off_x), int(off_y)))
                return
            # Fallback to normal draw if anything goes wrong
        # Default: draw normally via Ship
        ship.draw(self.scene, facing_right=facing_right, fg_color=FG_COLOR, accent=ACCENT)

    def _prepare_background(self):
        self._bg_prepared = make_starfield_surface(
            WIDTH,
            HEIGHT,
            density=STAR_DENSITY,
            size_min=STAR_SIZE_MIN,
            size_max=STAR_SIZE_MAX,
            bg_color=(0, 0, 0),
        )


if __name__ == "__main__":
    QuickdrawGame().run()
