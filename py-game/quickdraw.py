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
import random

try:
    import pygame
except Exception as e:  # pragma: no cover - runtime check for friendly error
    print("pygame is required to run this game.\nInstall with: pip install pygame", file=sys.stderr)
    raise

# Use Quickdraw-specific config for sizes, colors, and FPS
from configs.quickdraw import (
    BASE_WIDTH, BASE_HEIGHT, WINDOW_SCALE,
    FPS,
    BG_COLOR, FG_COLOR, ACCENT,
    SHIP_HEIGHT_FRAC as SHIP_H_FRAC,
    SHIP_ASPECT_SCALE,
    SHIP_MARGIN_FRAC,
    GROUND_FRAC, FOOT_MARGIN_PX,
    FULLSCREEN_DEFAULT,
    STAR_DENSITY, STAR_SIZE_MIN, STAR_SIZE_MAX,
)

# Logical world size (fixed) and initial display size
WIDTH, HEIGHT = BASE_WIDTH, BASE_HEIGHT
INITIAL_DISPLAY_SIZE = (int(BASE_WIDTH * WINDOW_SCALE), int(BASE_HEIGHT * WINDOW_SCALE))

# Ship sizing and placement derived from config
SHIP_W = int(HEIGHT * SHIP_H_FRAC * SHIP_ASPECT_SCALE)
SHIP_H = int(HEIGHT * SHIP_H_FRAC)
MARGIN_X = int(WIDTH * SHIP_MARGIN_FRAC)

from controls import ControlsMixin
from sprites import Ship
from sprites.background import make_starfield_surface


class QuickdrawGame(ControlsMixin):
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Space Cowboy Quickdraw")
        # Initialize display based on config
        self.fullscreen = bool(FULLSCREEN_DEFAULT)
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode(INITIAL_DISPLAY_SIZE, pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)
        self.scene = pygame.Surface((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 28)
        self.big_font = pygame.font.SysFont("monospace", 72)
        self.med_font = pygame.font.SysFont("monospace", 40)

        self._bg_prepared = None
        self._prepare_background()

        # Assets: specific facing/state sprites
        spr_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sprites", "images")
        self.left_holstered = os.path.join(spr_dir, "space-cowboy-holstered-east-facing.png")
        self.right_holstered = os.path.join(spr_dir, "space-cowboy-holstered-west-facing.png")
        self.left_drawn = os.path.join(spr_dir, "space-cowboy-drawn-east-facing.png")
        self.right_drawn = os.path.join(spr_dir, "space-cowboy-drawn-west-facing.png")

        # Place cowboys near the ground line defined by config
        ground_y = int(HEIGHT * GROUND_FRAC)
        base_y = ground_y - FOOT_MARGIN_PX - SHIP_H
        self.left = Ship(MARGIN_X, base_y, SHIP_W, SHIP_H, HEIGHT, image_path=self.left_holstered)
        self.right = Ship(WIDTH - MARGIN_X - SHIP_W, base_y, SHIP_W, SHIP_H, HEIGHT, image_path=self.right_holstered)

        # State machine
        self.running = True
        self.waiting_for_start = True
        self.countdown_start_ms = None
        self.countdown_total = 3000  # ms
        self.draw_signal_ms = None  # when "DRAW!" appeared
        self.draw_enabled = False
        self.winner = None  # 0 left, 1 right
        self.foul_by = None  # player index who drew too soon

        # Ready/Set/Draw phase control
        self.phase = None  # "ready" | "set" | "delay" | "draw" | None
        self.phase_start_ms = None
        self.random_delay_ms = None

        # Input edge detection for BLE
        self._ble_prev = (0, 0)

        # Winner animation timing
        self.win_anim_start_ms = None
        self.win_anim_duration = 1400  # ms

        # Bullet animation state (spawned only if not a foul)
        self.bullet_active = False
        self.bullet_from = None  # 0 left, 1 right
        self.bullet_to = None
        self.bullet_start = (0.0, 0.0)
        self.bullet_end = (0.0, 0.0)
        self.bullet_start_ms = None
        self.bullet_duration = 350  # ms flight

        # Kill effect for loser after bullet impact
        self.kill_target = None
        self.kill_start_ms = None
        self.kill_duration = 900  # ms

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
        # Initialize Ready/Set/Draw sequence
        self.phase = "ready"
        self.phase_start_ms = self.countdown_start_ms
        self.random_delay_ms = random.randint(500, 2000)
        # Clear any previous bullet/kill state
        self.bullet_active = False
        self.bullet_from = None
        self.bullet_to = None
        self.bullet_start = (0.0, 0.0)
        self.bullet_end = (0.0, 0.0)
        self.bullet_start_ms = None
        self.kill_target = None
        self.kill_start_ms = None

    def _restart(self):
        self.waiting_for_start = True
        self.winner = None
        self.foul_by = None
        self.countdown_start_ms = None
        self.draw_signal_ms = None
        self.draw_enabled = False
        self.phase = None
        self.phase_start_ms = None
        self.random_delay_ms = None
        self._ble_prev = (0, 0)
        self.win_anim_start_ms = None
        # Clear bullet/kill state
        self.bullet_active = False
        self.bullet_from = None
        self.bullet_to = None
        self.bullet_start = (0.0, 0.0)
        self.bullet_end = (0.0, 0.0)
        self.bullet_start_ms = None
        self.kill_target = None
        self.kill_start_ms = None
        # Reset sprites to holstered state
        self._set_player_pose(0, drawn=False)
        self._set_player_pose(1, drawn=False)
        # recenters to ground-based placement
        ground_y = int(HEIGHT * GROUND_FRAC)
        base_y = ground_y - FOOT_MARGIN_PX - SHIP_H
        self.left.y = base_y
        self.right.y = base_y
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
            # Winner switches to drawn pose
            self._set_player_pose(who, drawn=True)
            # Spawn bullet unless there was a foul
            if self.foul_by is None:
                self._spawn_bullet(from_player=who, to_player=1 - who)

    def _declare_foul(self, who: int):
        # A player drew before DRAW: they lose, the other wins.
        if self.winner is not None:
            return
        # Reset countdown/draw timing so no timer overlays linger
        self.countdown_start_ms = None
        self.draw_signal_ms = None
        self.draw_enabled = False
        self.phase = None
        self.phase_start_ms = None
        self.foul_by = who
        self._declare_winner(1 - who)

    def _update_state(self, now_ms: int):
        if self.waiting_for_start:
            return
        # Handle Ready/Set/Random delay -> DRAW phase transitions
        if not self.draw_enabled and self.phase is not None and self.phase_start_ms is not None:
            elapsed = now_ms - self.phase_start_ms
            if self.phase == "ready" and elapsed >= 1000:
                self.phase = "set"
                self.phase_start_ms = now_ms
            elif self.phase == "set" and elapsed >= 1000:
                self.phase = "delay"
                self.phase_start_ms = now_ms
            elif self.phase == "delay" and self.random_delay_ms is not None and elapsed >= self.random_delay_ms:
                # Start DRAW phase
                self.phase = "draw"
                self.draw_enabled = True
                self.draw_signal_ms = now_ms
        # Winner animation expiry handled in draw; no movement in this game

        # Advance bullet and trigger kill when it completes
        if self.bullet_active and self.bullet_start_ms is not None:
            t = (now_ms - self.bullet_start_ms) / float(self.bullet_duration)
            if t >= 1.0:
                self.bullet_active = False
                # Trigger kill effect on loser
                self.kill_target = self.bullet_to
                self.kill_start_ms = now_ms

    # --------------------------- Rendering --------------------------------
    def _draw(self, now_ms: int):
        if self._bg_prepared is not None:
            self.scene.blit(self._bg_prepared, (0, 0))
        else:
            self.scene.fill(BG_COLOR)

        # Draw players (with winner animation). Images are already correctly oriented,
        # so we pass facing_right=True to avoid flipping.
        self._draw_player(self.left, facing_right=True, now_ms=now_ms, is_winner=(self.winner == 0), is_kill_target=(self.kill_target == 0))
        self._draw_player(self.right, facing_right=True, now_ms=now_ms, is_winner=(self.winner == 1), is_kill_target=(self.kill_target == 1))

    # Bullet (on top of players)
        if self.bullet_active and self.bullet_start_ms is not None:
            t = max(0.0, min(1.0, (now_ms - self.bullet_start_ms) / float(self.bullet_duration)))
            sx, sy = self.bullet_start
            ex, ey = self.bullet_end
            bx = sx + (ex - sx) * t
            by = sy + (ey - sy) * t
            # Simple bullet: small yellow oval with faint trail
            bullet_color = (240, 220, 80)
            trail_color = (240, 220, 80, 90)
            # Trail: a few faded circles behind
            for i in range(1, 4):
                ft = max(0.0, t - i * 0.06)
                tx = sx + (ex - sx) * ft
                ty = sy + (ey - sy) * ft
                r = 3 - i  # shrinking
                if r > 0:
                    surf = pygame.Surface((r*2+1, r*2+1), pygame.SRCALPHA)
                    pygame.draw.circle(surf, trail_color, (r, r), r)
                    self.scene.blit(surf, (int(tx - r), int(ty - r)))
            pygame.draw.circle(self.scene, bullet_color, (int(bx), int(by)), 3)

        # Player labels (dim when outcome is shown to avoid clashing with winner/foul text)
        dim = self.winner is not None
        self._draw_nameplate(self.left, "Player 1", dimmed=dim)
        self._draw_nameplate(self.right, "Player 2", dimmed=dim)

        # UI overlays
        if self.waiting_for_start:
            self._overlay_center(self.big_font, "Quickdraw Duel", FG_COLOR, y=HEIGHT//2 - 80)
            self._overlay_center(self.font, "Press SPACE or ENTER to arm", FG_COLOR, y=HEIGHT//2 + 8)
        else:
            if self.winner is None:
                # Show phase text: READY -> Set -> (silent random delay) -> DRAW! with distinct colors and background
                if self.phase == "ready":
                    self._overlay_center_banner(self.med_font, "READY", (230, 70, 70), y=HEIGHT//2 - 60)
                elif self.phase == "set":
                    self._overlay_center_banner(self.med_font, "Set", (240, 210, 80), y=HEIGHT//2 - 60)
                elif self.phase == "draw":
                    if self.draw_signal_ms is not None and (now_ms - self.draw_signal_ms) < 900:
                        self._overlay_center_banner(self.med_font, "DRAW!", ACCENT, y=HEIGHT//2 - 60)

        if self.winner is not None:
            if self.foul_by is not None:
                # Show foul message prominently
                player = "Player 1" if self.foul_by == 0 else "Player 2"
                self._overlay_center(self.med_font, f"Too soon, {player} you lose!", (240, 120, 120), y=HEIGHT//2 - 160)
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

    def _overlay_center_banner(self, font, text: str, text_color, *, y: int, bg_alpha: int = 140, pad_x: int = 12, pad_y: int = 8):
        # Render centered text with a semi-transparent dark background for readability
        label = font.render(text, True, text_color)
        tx = WIDTH // 2 - label.get_width() // 2
        ty = y
        bg_rect = pygame.Rect(tx - pad_x, ty - pad_y, label.get_width() + pad_x * 2, label.get_height() + pad_y * 2)
        bg = pygame.Surface((bg_rect.w, bg_rect.h), pygame.SRCALPHA)
        bg.fill((0, 0, 0, bg_alpha))
        try:
            pygame.draw.rect(bg, (0, 0, 0, bg_alpha), bg.get_rect(), border_radius=8)
        except Exception:
            pass
        self.scene.blit(bg, (bg_rect.x, bg_rect.y))
        self.scene.blit(label, (tx, ty))

    def _draw_nameplate(self, ship: Ship, text: str, *, dimmed: bool = False):
        # Render a small semi-transparent banner below the player's sprite
        label = self.font.render(text, True, FG_COLOR)
        pad_x, pad_y = 8, 4
        tx = int(ship.x + ship.w // 2 - label.get_width() // 2)
        # Place under the sprite, clamp to bottom margin
        ty = int(min(HEIGHT - label.get_height() - 4, ship.y + ship.h + 6))
        bg_rect = pygame.Rect(tx - pad_x, ty - pad_y, label.get_width() + pad_x * 2, label.get_height() + pad_y * 2)
        # Adjust alphas when dimmed so end-of-round text stands out
        bg_alpha = 140 if not dimmed else 60
        text_alpha = 255 if not dimmed else 120
        bg = pygame.Surface((bg_rect.w, bg_rect.h), pygame.SRCALPHA)
        bg.fill((0, 0, 0, bg_alpha))
        # Optional rounded corners if supported by pygame.draw
        try:
            pygame.draw.rect(bg, (0, 0, 0, bg_alpha), bg.get_rect(), border_radius=6)
        except Exception:
            pass
        self.scene.blit(bg, (bg_rect.x, bg_rect.y))
        try:
            label.set_alpha(text_alpha)
        except Exception:
            pass
        self.scene.blit(label, (tx, ty))

    def _draw_player(self, ship: Ship, *, facing_right: bool, now_ms: int, is_winner: bool, is_kill_target: bool = False):
        # Kill effect overrides normal drawing for the losing player once triggered
        if is_kill_target and self.kill_start_ms is not None:
            prog = max(0.0, min(1.0, (now_ms - self.kill_start_ms) / float(self.kill_duration)))
            # Visual: fade out, slight rotate and drop
            angle = -12.0 * prog  # small tilt
            drop = ship.h * 0.18 * prog
            alpha = int(255 * (1.0 - prog))
            try:
                ship._ensure_images()  # type: ignore[attr-defined]
                base = ship._img_right if facing_right else ship._img_left  # type: ignore[attr-defined]
            except Exception:
                base = None
            if base is not None:
                img = base.copy()
                img.set_alpha(alpha)
                rotated = pygame.transform.rotozoom(img, angle, 1.0)
                rw, rh = rotated.get_width(), rotated.get_height()
                off_x = ship.x + (ship.w - rw) // 2
                off_y = ship.y + (ship.h - rh) // 2 + int(drop)
                self.scene.blit(rotated, (int(off_x), int(off_y)))
                return
            # Fallback to default if we can't apply effect
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
        """Load and crop the western background to cover the world size.

        Uses a "cover" fit: maintains aspect ratio, scales up so the image fully
        covers (WIDTH x HEIGHT), then center-crops to exactly that size.
        Falls back to the starfield if the image isn't available.
        """
        try:
            bg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sprites", "images", "western-background.png")
            if os.path.isfile(bg_path):
                src = pygame.image.load(bg_path).convert()
                iw, ih = src.get_width(), src.get_height()
                if iw > 0 and ih > 0:
                    # Cover-fit scaling
                    scale = max(WIDTH / iw, HEIGHT / ih)
                    new_w = max(1, int(math.ceil(iw * scale)))
                    new_h = max(1, int(math.ceil(ih * scale)))
                    scaled = pygame.transform.smoothscale(src, (new_w, new_h))

                    # Center-crop to (WIDTH, HEIGHT)
                    off_x = (new_w - WIDTH) // 2
                    off_y = (new_h - HEIGHT) // 2
                    canvas = pygame.Surface((WIDTH, HEIGHT))
                    canvas.blit(scaled, (-off_x, -off_y))
                    self._bg_prepared = canvas
                    return
        except Exception:
            # Fall back to procedural starfield below
            pass

        # Fallback background
        self._bg_prepared = make_starfield_surface(
            WIDTH,
            HEIGHT,
            density=STAR_DENSITY,
            size_min=STAR_SIZE_MIN,
            size_max=STAR_SIZE_MAX,
            bg_color=BG_COLOR,
        )

    def _set_player_pose(self, who: int, *, drawn: bool):
        """Swap the player's sprite between holstered/drawn and clear caches.
        Images are pre-oriented (east for left, west for right), so we avoid flips by
        always drawing with facing_right=True.
        """
        ship = self.left if who == 0 else self.right
        if who == 0:
            path = self.left_drawn if drawn else self.left_holstered
        else:
            path = self.right_drawn if drawn else self.right_holstered
        if os.path.isfile(path):
            ship.image_path = path
            # Clear cached images so the new sprite loads next draw
            try:
                ship._img_right = None  # type: ignore[attr-defined]
                ship._img_left = None   # type: ignore[attr-defined]
            except Exception:
                pass

    def _spawn_bullet(self, *, from_player: int, to_player: int):
        # Determine start and end coordinates based on ship bounds
        shooter = self.left if from_player == 0 else self.right
        target = self.left if to_player == 0 else self.right
        # Approximate muzzle position as slightly forward from ship center
        sx = shooter.x + (shooter.w * (0.80 if from_player == 0 else 0.20))
        sy = shooter.y + int(shooter.h * 0.55)
        # Target around mid-torso
        ex = target.x + (target.w * (0.20 if to_player == 0 else 0.80))
        ey = target.y + int(target.h * 0.50)
        self.bullet_active = True
        self.bullet_from = from_player
        self.bullet_to = to_player
        self.bullet_start = (float(sx), float(sy))
        self.bullet_end = (float(ex), float(ey))
        self.bullet_start_ms = pygame.time.get_ticks()


if __name__ == "__main__":
    QuickdrawGame().run()
