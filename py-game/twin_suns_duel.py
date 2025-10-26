#!/usr/bin/python3
"""
Twin Suns Duel: A minimalist, high-tension binary duel between two space cowboys.

Inputs per player are continuous in [0,1]:
- input > ATTACK_THRESHOLD => Shoot (Attack)
- input <= ATTACK_THRESHOLD => Deflect (Block)

Rules
- You have only 3 seconds total of shield. While blocking, your shield drains.
- When shield hits 0, your guard breaks and you cannot block anymore this round.
- You win by attacking while your opponent is not blocking (either they are attacking or guard-broken).
- Simultaneous attacks cancel each other (no hit that frame).

Keyboard mapping
- Player 1: hold W to Attack (value 1.0), release for Block (0.0)
- Player 2: hold Up Arrow to Attack (value 1.0), release for Block (0.0)

BLE mapping
- If ControlsMixin.poll_ble() returns non-zero for a player, treat it as 1.0; otherwise 0.0.

Run
  python3 py-game/twin_suns_duel.py
"""

from __future__ import annotations

import math
import os
import sys
from typing import Optional, Tuple

try:
    import pygame
except Exception as e:
    print("pygame is required to run this game.\nInstall with: pip install pygame", file=sys.stderr)
    raise

from configs.twin_suns_duel import (
    BASE_WIDTH, BASE_HEIGHT, WINDOW_SCALE,
    FPS,
    BG_COLOR, FG_COLOR, ACCENT, ALERT, WARNING,
    ATTACK_THRESHOLD, SHIELD_MAX_SECONDS,
    SHIP_HEIGHT_FRAC, SHIP_ASPECT_SCALE, SHIP_MARGIN_FRAC, GROUND_FRAC, FOOT_MARGIN_PX,
    INPUT_BAR_WIDTH_FRAC, INPUT_BAR_HEIGHT, SHIELD_BAR_HEIGHT, GAUGE_MARGIN_PX,
    TEXT_OUTLINE_PX, TEXT_OUTLINE_COLOR,
    FULLSCREEN_DEFAULT,
    STAR_DENSITY, STAR_SIZE_MIN, STAR_SIZE_MAX,
    FONT_PATH,
)

WIDTH, HEIGHT = BASE_WIDTH, BASE_HEIGHT
INITIAL_DISPLAY_SIZE = (int(BASE_WIDTH * WINDOW_SCALE), int(BASE_HEIGHT * WINDOW_SCALE))

from controls import ControlsMixin
from fonts.fonts import load_fonts
from sprites.background import make_starfield_surface
from sprites import Ship


class TwinSunsDuel(ControlsMixin):
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Twin Suns Duel")
        self.fullscreen = bool(FULLSCREEN_DEFAULT)
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode(INITIAL_DISPLAY_SIZE, pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)
        self.scene = pygame.Surface((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        f = load_fonts(small=24, medium=36, big=56, font_path=FONT_PATH)
        self.font = f.small
        self.med_font = f.medium
        self.big_font = f.big

        self._bg = make_starfield_surface(WIDTH, HEIGHT, density=STAR_DENSITY, size_min=STAR_SIZE_MIN, size_max=STAR_SIZE_MAX, bg_color=BG_COLOR)

        # Sprites: use shield for default (block), blaster for attack; east faces right (left player), west faces left (right player)
        spr_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sprites", "images")
        self.left_shield = os.path.join(spr_dir, "cowboy-shield-east.png")
        self.right_shield = os.path.join(spr_dir, "cowboy-shield-west.png")
        self.left_blaster = os.path.join(spr_dir, "cowboy-blaster-east.png")
        self.right_blaster = os.path.join(spr_dir, "cowboy-blaster-west.png")

        # Size/placement
        self.SHIP_W = int(HEIGHT * SHIP_HEIGHT_FRAC * SHIP_ASPECT_SCALE)
        self.SHIP_H = int(HEIGHT * SHIP_HEIGHT_FRAC)
        self.MARGIN_X = int(WIDTH * SHIP_MARGIN_FRAC)
        ground_y = int(HEIGHT * GROUND_FRAC)
        base_y = ground_y - FOOT_MARGIN_PX - self.SHIP_H

        self.left_ship = Ship(self.MARGIN_X, base_y, self.SHIP_W, self.SHIP_H, HEIGHT, image_path=self.left_shield)
        self.right_ship = Ship(WIDTH - self.MARGIN_X - self.SHIP_W, base_y, self.SHIP_W, self.SHIP_H, HEIGHT, image_path=self.right_shield)
        self.left_attacking = False
        self.right_attacking = False

        # State
        self.running = True
        self.waiting_for_start = True
        self.winner = None  # 0 for left, 1 for right
        self.guard_broken = [False, False]
        self.shield_remaining = [SHIELD_MAX_SECONDS, SHIELD_MAX_SECONDS]

        # Input smoothing (optional)
        self.input_val = [0.0, 0.0]
        self.input_alpha = 0.50  # EMA smoothing

    # --------------------------- Main loop --------------------------------
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    if not self.fullscreen:
                        self.screen = pygame.display.set_mode(event.size, pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        self.running = False
                    elif event.key == pygame.K_F11:
                        self._toggle_fullscreen()
                    elif event.key == pygame.K_r:
                        self._restart()
                    elif self.waiting_for_start and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        self.waiting_for_start = False

            if not self.waiting_for_start and self.winner is None:
                self._update(dt)

            self._draw()

        pygame.quit()

    def _toggle_fullscreen(self):
        if self.fullscreen:
            self.screen = pygame.display.set_mode(INITIAL_DISPLAY_SIZE, pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)
            self.fullscreen = False
        else:
            self.screen = pygame.display.set_mode((0, 0), pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.FULLSCREEN)
            self.fullscreen = True

    def _restart(self):
        self.waiting_for_start = True
        self.winner = None
        self.guard_broken = [False, False]
        self.shield_remaining = [SHIELD_MAX_SECONDS, SHIELD_MAX_SECONDS]
        self.input_val = [0.0, 0.0]

    # --------------------------- Game logic -------------------------------
    def _read_inputs(self) -> Tuple[float, float]:
        # Keyboard -> binary analog: held => 1.0, else 0.0
        keys = pygame.key.get_pressed()
        kb1 = 1.0 if keys[pygame.K_w] else 0.0
        kb2 = 1.0 if keys[pygame.K_UP] else 0.0
        # BLE -> any non-zero => 1.0
        try:
            b1, b2 = self.poll_ble()
        except Exception:
            b1, b2 = 0, 0
        ble1 = 1.0 if b1 != 0 else 0.0
        ble2 = 1.0 if b2 != 0 else 0.0
        # Prefer BLE when present, else keyboard
        v1 = ble1 if ble1 > 0.0 else kb1
        v2 = ble2 if ble2 > 0.0 else kb2
        return v1, v2

    def _update(self, dt: float):
        # Inputs (EMA smoothing for slightly nicer bars)
        v1, v2 = self._read_inputs()
        self.input_val[0] = self.input_alpha * v1 + (1 - self.input_alpha) * self.input_val[0]
        self.input_val[1] = self.input_alpha * v2 + (1 - self.input_alpha) * self.input_val[1]

        # Determine intents
        attacking = [False, False]
        blocking = [False, False]
        for i, v in enumerate(self.input_val):
            atk = v > ATTACK_THRESHOLD
            can_block = not self.guard_broken[i] and self.shield_remaining[i] > 0.0
            attacking[i] = atk
            blocking[i] = (not atk) and can_block

        # Update sprite poses
        self.left_attacking = attacking[0]
        self.right_attacking = attacking[1]
        self._set_player_pose(0, attack=self.left_attacking)
        self._set_player_pose(1, attack=self.right_attacking)

        # Drain shields while blocking
        for i in (0, 1):
            if blocking[i]:
                self.shield_remaining[i] = max(0.0, self.shield_remaining[i] - dt)
                if self.shield_remaining[i] <= 0.0:
                    self.guard_broken[i] = True

        # Resolve hits (instantaneous)
        # A hits if A attacks and B is not blocking.
        p1_hits = attacking[0] and not blocking[1]
        p2_hits = attacking[1] and not blocking[0]
        # Simultaneous hits cancel
        if p1_hits and p2_hits:
            pass  # clash: no winner this frame
        elif p1_hits:
            self.winner = 0
        elif p2_hits:
            self.winner = 1

    # --------------------------- Rendering --------------------------------
    def _draw(self):
        self.scene.blit(self._bg, (0, 0))

        # Optional ground line for style
        pygame.draw.line(self.scene, (64, 64, 76), (0, int(HEIGHT * GROUND_FRAC)), (WIDTH, int(HEIGHT * GROUND_FRAC)), 2)

        # Draw players (images are pre-oriented: left uses east, right uses west)
        # Pass facing_right=True to avoid flips and use the source orientation
        self.left_ship.draw(self.scene, facing_right=True, fg_color=FG_COLOR, accent=ACCENT)
        self.right_ship.draw(self.scene, facing_right=True, fg_color=FG_COLOR, accent=ACCENT)

        # Title / prompts
        y0 = 24
        if self.waiting_for_start:
            self._draw_center_outlined(self.big_font, "Twin Suns Duel", FG_COLOR, y0)
            self._draw_center_outlined(self.font, "Press SPACE or ENTER to start", FG_COLOR, y0 + 40)
        elif self.winner is None:
            self._draw_center_outlined(self.med_font, "1 = Shoot  |  0 = Deflect", FG_COLOR, y0)
        else:
            msg = "Player 1 Wins!" if self.winner == 0 else "Player 2 Wins!"
            self._draw_center_outlined(self.med_font, msg, FG_COLOR, y0)
            self._draw_center_outlined(self.font, "Press R to restart • Q to quit", FG_COLOR, y0 + 36)

        # Gauges
        self._draw_gauges()

        # Present
        display_size = self.screen.get_size()
        scaled = pygame.transform.smoothscale(self.scene, display_size)
        self.screen.blit(scaled, (0, 0))
        pygame.display.flip()

    def _draw_gauges(self):
        # Layout: P1 left, P2 right; input bars above shield bars.
        bar_w = int(WIDTH * INPUT_BAR_WIDTH_FRAC)
        in_h = INPUT_BAR_HEIGHT
        sh_h = SHIELD_BAR_HEIGHT
        gap = GAUGE_MARGIN_PX
        top_y = HEIGHT // 2 - in_h - sh_h - gap // 2

        # Player 1 (left)
        x1 = gap
        self._draw_input_bar(x1, top_y, bar_w, in_h, self.input_val[0], ATTACK_THRESHOLD)
        shield_frac1 = max(0.0, min(1.0, self.shield_remaining[0] / SHIELD_MAX_SECONDS))
        self._draw_shield_bar(x1, top_y + in_h + 6, bar_w, sh_h, shield_frac1, broken=self.guard_broken[0])

        # Player 2 (right)
        x2 = WIDTH - gap - bar_w
        self._draw_input_bar(x2, top_y, bar_w, in_h, self.input_val[1], ATTACK_THRESHOLD)
        shield_frac2 = max(0.0, min(1.0, self.shield_remaining[1] / SHIELD_MAX_SECONDS))
        self._draw_shield_bar(x2, top_y + in_h + 6, bar_w, sh_h, shield_frac2, broken=self.guard_broken[1])

        # Labels
        self._draw_text_outlined(self.font, "Player 1", FG_COLOR, x1, top_y - 24)
        self._draw_text_outlined(self.font, "Player 2", FG_COLOR, x2 + bar_w - self.font.size("Player 2")[0], top_y - 24)

    def _draw_input_bar(self, x: int, y: int, w: int, h: int, v: float, threshold: float):
        # Background
        pygame.draw.rect(self.scene, (30, 30, 36), (x, y, w, h), border_radius=4)
        # Fill for current input value
        val_w = int(max(0, min(w, round(w * max(0.0, min(1.0, v))))))
        color = ALERT if v > threshold else ACCENT
        pygame.draw.rect(self.scene, color, (x, y, val_w, h), border_radius=4)
        # Threshold marker
        t_x = x + int(round(w * threshold))
        pygame.draw.line(self.scene, WARNING, (t_x, y), (t_x, y + h), 2)

    def _draw_shield_bar(self, x: int, y: int, w: int, h: int, frac: float, *, broken: bool):
        # Background
        pygame.draw.rect(self.scene, (30, 30, 36), (x, y, w, h), border_radius=4)
        # Fill
        fill_w = int(max(0, min(w, round(w * frac))))
        col = FG_COLOR if not broken else (140, 60, 60)
        pygame.draw.rect(self.scene, col, (x, y, fill_w, h), border_radius=4)
        # Border
        pygame.draw.rect(self.scene, (60, 60, 70), (x, y, w, h), width=1, border_radius=4)

    # --------------------------- Text helpers -----------------------------
    def _draw_center_outlined(self, font, text: str, color, y: int):
        label_main = font.render(text, True, color)
        outline = font.render(text, True, TEXT_OUTLINE_COLOR)
        tx = WIDTH // 2 - label_main.get_width() // 2
        ty = y
        for dx, dy in [(-TEXT_OUTLINE_PX, 0), (TEXT_OUTLINE_PX, 0), (0, -TEXT_OUTLINE_PX), (0, TEXT_OUTLINE_PX),
                        (-TEXT_OUTLINE_PX, -TEXT_OUTLINE_PX), (-TEXT_OUTLINE_PX, TEXT_OUTLINE_PX), (TEXT_OUTLINE_PX, -TEXT_OUTLINE_PX), (TEXT_OUTLINE_PX, TEXT_OUTLINE_PX)]:
            self.scene.blit(outline, (tx + dx, ty + dy))
        self.scene.blit(label_main, (tx, ty))

    def _draw_text_outlined(self, font, text: str, color, x: int, y: int):
        label_main = font.render(text, True, color)
        outline = font.render(text, True, TEXT_OUTLINE_COLOR)
        for dx, dy in [(-TEXT_OUTLINE_PX, 0), (TEXT_OUTLINE_PX, 0), (0, -TEXT_OUTLINE_PX), (0, TEXT_OUTLINE_PX),
                        (-TEXT_OUTLINE_PX, -TEXT_OUTLINE_PX), (-TEXT_OUTLINE_PX, TEXT_OUTLINE_PX), (TEXT_OUTLINE_PX, -TEXT_OUTLINE_PX), (TEXT_OUTLINE_PX, TEXT_OUTLINE_PX)]:
            self.scene.blit(outline, (x + dx, y + dy))
        self.scene.blit(label_main, (x, y))

    # --------------------------- Sprites ---------------------------------
    def _set_player_pose(self, who: int, *, attack: bool):
        ship = self.left_ship if who == 0 else self.right_ship
        if who == 0:
            path = self.left_blaster if attack else self.left_shield
        else:
            path = self.right_blaster if attack else self.right_shield
        if os.path.isfile(path):
            ship.image_path = path
            try:
                ship._img_right = None  # type: ignore[attr-defined]
                ship._img_left = None   # type: ignore[attr-defined]
            except Exception:
                pass


if __name__ == "__main__":
    TwinSunsDuel().run()
