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
import random
import pygame

from typing import Optional, Tuple
from .controls import Controls
from .fonts.fonts import load_fonts
from .sprites import Ship
from .sprites.background import make_starfield_surface

# Use Quickdraw-specific config for sizes, colors, and FPS
from .configs.quickdraw import (
    BASE_WIDTH, BASE_HEIGHT, WINDOW_SCALE,
    FPS,
    BG_COLOR, FG_COLOR, ACCENT,
    SHIP_HEIGHT_FRAC as SHIP_H_FRAC,
    SHIP_ASPECT_SCALE,
    SHIP_MARGIN_FRAC,
    GROUND_FRAC, FOOT_MARGIN_PX,
    FULLSCREEN_DEFAULT,
    TEXT_OUTLINE_PX, TEXT_OUTLINE_COLOR,
    STAR_DENSITY, STAR_SIZE_MIN, STAR_SIZE_MAX,
    FONT_PATH,
)

# Logical world size (fixed) and initial display size
WIDTH, HEIGHT = BASE_WIDTH, BASE_HEIGHT
INITIAL_DISPLAY_SIZE = (int(BASE_WIDTH * WINDOW_SCALE), int(BASE_HEIGHT * WINDOW_SCALE))

# Ship sizing and placement derived from config
SHIP_W = int(HEIGHT * SHIP_H_FRAC * SHIP_ASPECT_SCALE)
SHIP_H = int(HEIGHT * SHIP_H_FRAC)
MARGIN_X = int(WIDTH * SHIP_MARGIN_FRAC)


class QuickdrawGame(Controls):
    def __init__(self, *, controls:Controls, screen: Optional[pygame.Surface] = None, own_display: bool | None = None):
        super().__init__()
        pygame.init()
        # Determine if this game owns the display (standalone) or uses a shared window (hosted)
        self._owns_display = bool(own_display) if own_display is not None else (screen is None)
        if self._owns_display:
            pygame.display.set_caption("MYO BEBOP Quickdraw")
            # Initialize display based on config
            self.fullscreen = bool(FULLSCREEN_DEFAULT)
            if self.fullscreen:
                self.screen = pygame.display.set_mode((0, 0), pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.FULLSCREEN)
            else:
                self.screen = pygame.display.set_mode(INITIAL_DISPLAY_SIZE, pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)
        else:
            # Hosted: reuse provided screen and do not change display mode
            self.screen = screen  # type: ignore[assignment]
            self.fullscreen = pygame.display.get_surface() is not None and pygame.display.get_window_size() == pygame.display.get_surface().get_size()
            try:
                pygame.display.set_caption("MYO BEBOP Quickdraw")
            except Exception:
                pass
        self.scene = pygame.Surface((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        # Optional BLE provider for Controls
        self.controls = controls
        # Load game fonts via shared loader
        fonts = load_fonts(small=28, medium=40, big=72, font_path=FONT_PATH)
        self.font = fonts.small
        self.med_font = fonts.medium
        self.big_font = fonts.big

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

        # Input edge detection (merged keyboard/BLE via Controls.get_data())
        self._bin_prev = (0.0, 0.0)

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
        self.bullet_duration = 250  # ms flight

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
            # Poll merged input each frame for 0->1 edges
            self._handle_draw_inputs()

            self._update_state(now)
            self._draw(now)

        if self._owns_display:
            pygame.quit()

    # --------------------------- State & Input ----------------------------
    def _arm_countdown(self):
        self.waiting_for_start = False
        self.winner = None
        self.foul_by = None
        self.countdown_start_ms = pygame.time.get_ticks()
        self.draw_signal_ms = None
        self.draw_enabled = False
        self._bin_prev = (0.0, 0.0)
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
        self._bin_prev = (0.0, 0.0)
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

    def _handle_draw_inputs(self):
        """Detect 0->1 edges from merged keyboard/BLE binary input.
        Before DRAW: edge is a foul; after DRAW: edge is a valid draw.
        """
        if self.winner is not None:
            return
        try:
            v1, v2 = self.controls.get_data(threshold=0.75)
        except Exception:
            v1, v2 = 0.0, 0.0
        p1_prev, p2_prev = self._bin_prev
        # Edge triggers
        if v1 > 0.5 and p1_prev <= 0.5:
            if not self.waiting_for_start and not self.draw_enabled:
                self._declare_foul(0)
            elif self.draw_enabled:
                self._declare_winner(0)
        elif v2 > 0.5 and p2_prev <= 0.5:
            if not self.waiting_for_start and not self.draw_enabled:
                self._declare_foul(1)
            elif self.draw_enabled:
                self._declare_winner(1)
        self._bin_prev = (v1, v2)

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
            self._overlay_center_outlined(self.big_font, "Quickdraw Duel", FG_COLOR, y=HEIGHT//2 - 80, outline_px=TEXT_OUTLINE_PX, outline_color=TEXT_OUTLINE_COLOR)
            self._overlay_center_outlined(self.font, "Press SPACE or ENTER to arm", FG_COLOR, y=HEIGHT//2 + 8, outline_px=TEXT_OUTLINE_PX, outline_color=TEXT_OUTLINE_COLOR)
        else:
            if self.winner is None:
                # Show phase text: READY -> Set -> (silent random delay) -> DRAW! with distinct colors and background
                if self.phase == "ready":
                    self._overlay_center_outlined(self.med_font, "READY", (230, 70, 70), y=HEIGHT//2 - 60, outline_px=TEXT_OUTLINE_PX, outline_color=TEXT_OUTLINE_COLOR)
                elif self.phase == "set":
                    self._overlay_center_outlined(self.med_font, "Set", (240, 210, 80), y=HEIGHT//2 - 60, outline_px=TEXT_OUTLINE_PX, outline_color=TEXT_OUTLINE_COLOR)
                elif self.phase == "draw":
                    if self.draw_signal_ms is not None and (now_ms - self.draw_signal_ms) < 900:
                        self._overlay_center_outlined(self.med_font, "DRAW!", ACCENT, y=HEIGHT//2 - 60, outline_px=TEXT_OUTLINE_PX, outline_color=TEXT_OUTLINE_COLOR)

        if self.winner is not None:
            if self.foul_by is not None:
                # Show foul message prominently
                player = "Player 1" if self.foul_by == 0 else "Player 2"
                self._overlay_center_outlined(self.med_font, f"Too soon, {player} you lose!", (240, 120, 120), y=HEIGHT//2 - 160, outline_px=TEXT_OUTLINE_PX, outline_color=TEXT_OUTLINE_COLOR)
                msg = "Player 1 wins!" if self.winner == 0 else "Player 2 wins!"
            else:
                msg = "Player 1 drew first!" if self.winner == 0 else "Player 2 drew first!"
            self._overlay_center_outlined(self.med_font, msg, (240, 210, 80), y=HEIGHT//2 - 120, outline_px=TEXT_OUTLINE_PX, outline_color=TEXT_OUTLINE_COLOR)
            self._overlay_center_outlined(self.font, "Press R to restart • Q to quit", FG_COLOR, y=HEIGHT//2 - 76, outline_px=TEXT_OUTLINE_PX, outline_color=TEXT_OUTLINE_COLOR)

        # Scale scene to display
        display_size = self.screen.get_size()
        scaled = pygame.transform.smoothscale(self.scene, display_size)
        self.screen.blit(scaled, (0, 0))
        pygame.display.flip()

    def _overlay_center(self, font, text: str, color, *, y: int):
        surf = font.render(text, True, color)
        self.scene.blit(surf, (WIDTH // 2 - surf.get_width() // 2, y))

    def _overlay_center_outlined(self, font, text: str, text_color, *, y: int, outline_px: int | None = None, outline_color = None, alpha: int | None = None):
        # Render centered outlined text by rendering outline and main separately
        if outline_px is None:
            outline_px = TEXT_OUTLINE_PX
        if outline_color is None:
            outline_color = TEXT_OUTLINE_COLOR
        label_main = font.render(text, True, text_color)
        label_outline = font.render(text, True, outline_color)
        tx = WIDTH // 2 - label_main.get_width() // 2
        ty = y
        if alpha is not None:
            try:
                label_outline.set_alpha(alpha)
                label_main.set_alpha(alpha)
            except Exception:
                pass
        # Draw outline first
        offsets = [
            (-outline_px, 0), (outline_px, 0), (0, -outline_px), (0, outline_px),
            (-outline_px, -outline_px), (-outline_px, outline_px), (outline_px, -outline_px), (outline_px, outline_px),
        ]
        for dx, dy in offsets:
            self.scene.blit(label_outline, (tx + dx, ty + dy))
        # Draw main text
        self.scene.blit(label_main, (tx, ty))

    # (fonts are loaded via fonts.fonts)

    def _draw_nameplate(self, ship: Ship, text: str, *, dimmed: bool = False):
        # Render outlined title below the player's sprite (no background box)
        # Place under the sprite, clamp to bottom margin
        # Compute text width first using font metrics
        label_tmp = self.font.render(text, True, FG_COLOR)
        tx = int(ship.x + ship.w // 2 - label_tmp.get_width() // 2)
        ty = int(min(HEIGHT - label_tmp.get_height() - 4, ship.y + ship.h + 6))
        alpha = 255 if not dimmed else 140
        self._draw_text_outlined(self.font, text, FG_COLOR, tx, ty, outline_px=TEXT_OUTLINE_PX, outline_color=TEXT_OUTLINE_COLOR, alpha=alpha)

    def _draw_text_outlined(self, font, text: str, text_color, x: int, y: int, *, outline_px: int | None = None, outline_color = None, alpha: int | None = None):
        if outline_px is None:
            outline_px = TEXT_OUTLINE_PX
        if outline_color is None:
            outline_color = TEXT_OUTLINE_COLOR
        label_main = font.render(text, True, text_color)
        label_outline = font.render(text, True, outline_color)
        if alpha is not None:
            try:
                label_outline.set_alpha(alpha)
                label_main.set_alpha(alpha)
            except Exception:
                pass
        offsets = [
            (-outline_px, 0), (outline_px, 0), (0, -outline_px), (0, outline_px),
            (-outline_px, -outline_px), (-outline_px, outline_px), (outline_px, -outline_px), (outline_px, outline_px),
        ]
        for dx, dy in offsets:
            self.scene.blit(label_outline, (x + dx, y + dy))
        self.scene.blit(label_main, (x, y))

    def _blit_outlined_text(self, text_surface, pos: tuple[int, int], *, outline_px: int | None = None, outline_color = None, alpha: int | None = None):
        """Blit text with an outline by drawing the outline in 8 directions, then the text.
        text_surface should already be rendered.
        """
        if outline_px is None:
            outline_px = TEXT_OUTLINE_PX
        if outline_color is None:
            outline_color = TEXT_OUTLINE_COLOR
        x, y = pos
        # Create outline surface by re-rendering the same text with outline color
        try:
            # We need the font and text to re-render; infer from text_surface if possible is hard.
            # Instead approximate by tinting via per-surface alpha blend: re-render path preferred.
            # So accept only surfaces; we redraw outline by colorizing a copy.
            pass
        except Exception:
            pass
        # Since we have only the surface, render outline by offset blits of a solid-colored version
        outline = text_surface.copy()
        # Fill a solid color while preserving alpha via multiply: easiest is to fill and BLEND_RGBA_MULT then add color
        oc = outline_color
        try:
            # Set all RGB to outline color, keep alpha from glyph
            outline.fill((0, 0, 0, 0))
            mask = text_surface.copy()
            col_surf = pygame.Surface(mask.get_size(), pygame.SRCALPHA)
            col_surf.fill((*oc, 255))
            mask.blit(col_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            outline = mask
        except Exception:
            # Fallback: use original as outline
            outline = text_surface
        if alpha is not None:
            try:
                outline.set_alpha(alpha)
            except Exception:
                pass
        # Draw outline around
        offsets = [
            (-outline_px, 0), (outline_px, 0), (0, -outline_px), (0, outline_px),
            (-outline_px, -outline_px), (-outline_px, outline_px), (outline_px, -outline_px), (outline_px, outline_px),
        ]
        for dx, dy in offsets:
            self.scene.blit(outline, (x + dx, y + dy))
        # Draw main text
        main = text_surface
        if alpha is not None:
            try:
                main = text_surface.copy()
                main.set_alpha(alpha)
            except Exception:
                main = text_surface
        self.scene.blit(main, (x, y))

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
