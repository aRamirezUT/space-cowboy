#!/usr/bin/python3
"""
Twin Suns Duel: A minimalist, high-tension binary duel between two space cowboys.

Inputs per player are continuous in [0,1]:
- input > ATTACK_THRESHOLD => Shoot (Attack)
- input <= ATTACK_THRESHOLD => Deflect (Block)

Rules
- You have only 3 seconds total of shield. While blocking, your shield drains.
- While shooting, your shield regenerates slowly (slower than it drains).
- When shield hits 0, your guard breaks (you cannot block), and you can take damage.
- You only take damage if your shield has run out (<= 0).
- Simultaneous attacks cancel each other (no hit that frame), but still consume cooldown.

Keyboard mapping
- Player 1: hold W to Attack (value 1.0), release for Block (0.0)
- Player 2: hold Up Arrow to Attack (value 1.0), release for Block (0.0)

BLE mapping
- If Controls.poll_ble() returns non-zero for a player, treat it as 1.0; otherwise 0.0.

Run
  python3 py-game/twin_suns_duel.py
"""

from __future__ import annotations

import os
import pygame

from typing import Optional, Tuple
from .controls import Controls
from .fonts.fonts import load_fonts
from .sprites.background import make_starfield_surface
from .sprites import Ship

from .configs.twin_suns_duel import (
    BASE_WIDTH, BASE_HEIGHT, WINDOW_SCALE,
    FPS,
    BG_COLOR, FG_COLOR, ACCENT, ALERT, WARNING,
    ATTACK_THRESHOLD, SHIELD_MAX_SECONDS, SHIELD_REGEN_RATE,
    ATTACK_COOLDOWN_SECONDS,
    HEALTH_MAX, HEALTH_DAMAGE_FRACTION,
    SHIP_HEIGHT_FRAC, SHIP_ASPECT_SCALE, SHIP_MARGIN_FRAC, GROUND_FRAC, FOOT_MARGIN_PX,
    INPUT_BAR_WIDTH_FRAC, INPUT_BAR_HEIGHT, SHIELD_BAR_HEIGHT, HEALTH_BAR_HEIGHT, GAUGE_MARGIN_PX,
    TEXT_OUTLINE_PX, TEXT_OUTLINE_COLOR,
    FULLSCREEN_DEFAULT,
    STAR_DENSITY, STAR_SIZE_MIN, STAR_SIZE_MAX,
    FONT_PATH,
)

WIDTH, HEIGHT = BASE_WIDTH, BASE_HEIGHT
INITIAL_DISPLAY_SIZE = (int(BASE_WIDTH * WINDOW_SCALE), int(BASE_HEIGHT * WINDOW_SCALE))


class TwinSunsDuel(Controls):
    def __init__(self, *, screen: Optional[pygame.Surface] = None, own_display: bool | None = None, ble_client=None):
        super().__init__()
        pygame.init()
        pygame.display.set_caption("Twin Suns Duel")
        self._owns_display = bool(own_display) if own_display is not None else (screen is None)
        if self._owns_display:
            self.fullscreen = bool(FULLSCREEN_DEFAULT)
            if self.fullscreen:
                self.screen = pygame.display.set_mode((0, 0), pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.FULLSCREEN)
            else:
                self.screen = pygame.display.set_mode(INITIAL_DISPLAY_SIZE, pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)
        else:
            self.screen = screen  # type: ignore[assignment]
            # Keep current fullscreen/window state without forcing a change
            self.fullscreen = False
        # Optional BLE provider for Controls
        self.ble_provider = ble_client
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
        self.health = [HEALTH_MAX, HEALTH_MAX]
        self.attack_cooldown = [0.0, 0.0]  # seconds remaining until next shot allowed

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

        if self._owns_display:
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
        self.health = [HEALTH_MAX, HEALTH_MAX]
        self.attack_cooldown = [0.0, 0.0]
        self.input_val = [0.0, 0.0]

    # --------------------------- Game logic -------------------------------
    def _read_inputs(self) -> Tuple[float, float]:
        # Use Controls to merge keyboard/BLE (BLE has priority)
        try:
            return self.input_binary()
        except Exception:
            # Fallback: no input if something goes wrong
            return 0.0, 0.0

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

        # Update cooldown timers
        for i in (0, 1):
            if self.attack_cooldown[i] > 0.0:
                self.attack_cooldown[i] = max(0.0, self.attack_cooldown[i] - dt)

        # Update sprite poses
        self.left_attacking = attacking[0]
        self.right_attacking = attacking[1]
        self._set_player_pose(0, attack=self.left_attacking)
        self._set_player_pose(1, attack=self.right_attacking)

        # Drain shields while blocking; regenerate slowly while attacking
        for i in (0, 1):
            if blocking[i]:
                # Drain at 1.0 per second
                self.shield_remaining[i] = max(0.0, self.shield_remaining[i] - dt)
            elif attacking[i]:
                # Regenerate slowly while shooting, but not faster than it depletes
                self.shield_remaining[i] = min(SHIELD_MAX_SECONDS, self.shield_remaining[i] + SHIELD_REGEN_RATE * dt)
            # Update guard-broken state from current shield value
            self.guard_broken[i] = self.shield_remaining[i] <= 0.0

        # Resolve hits with fire-rate limiting: a shot only "fires" when cooldown is ready
        fired = [False, False]
        for i in (0, 1):
            if attacking[i] and self.attack_cooldown[i] <= 0.0:
                fired[i] = True
                self.attack_cooldown[i] = ATTACK_COOLDOWN_SECONDS

        # Damage is applied only if the target's shield is fully depleted
        p1_hits = fired[0] and (self.shield_remaining[1] <= 0.0)
        p2_hits = fired[1] and (self.shield_remaining[0] <= 0.0)
        # Simultaneous hits cancel
        if p1_hits and p2_hits:
            pass  # clash: no damage
        elif p1_hits:
            dmg = HEALTH_MAX * HEALTH_DAMAGE_FRACTION
            self.health[1] = max(0.0, self.health[1] - dmg)
            if self.health[1] <= 0.0:
                self.winner = 0
        elif p2_hits:
            dmg = HEALTH_MAX * HEALTH_DAMAGE_FRACTION
            self.health[0] = max(0.0, self.health[0] - dmg)
            if self.health[0] <= 0.0:
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
        hp_h = HEALTH_BAR_HEIGHT
        gap = GAUGE_MARGIN_PX
        total_h = in_h + sh_h + hp_h + 12  # extra spacing between groups
        top_y = HEIGHT // 2 - total_h // 2

        # Player 1 (left)
        x1 = gap
        self._draw_input_bar(x1, top_y, bar_w, in_h, self.input_val[0], ATTACK_THRESHOLD)
        shield_frac1 = max(0.0, min(1.0, self.shield_remaining[0] / SHIELD_MAX_SECONDS))
        self._draw_shield_bar(x1, top_y + in_h + 6, bar_w, sh_h, shield_frac1, broken=self.guard_broken[0])
        health_frac1 = max(0.0, min(1.0, self.health[0] / HEALTH_MAX))
        self._draw_health_bar(x1, top_y + in_h + 6 + sh_h + 6, bar_w, hp_h, health_frac1)

        # Player 2 (right)
        x2 = WIDTH - gap - bar_w
        self._draw_input_bar(x2, top_y, bar_w, in_h, self.input_val[1], ATTACK_THRESHOLD)
        shield_frac2 = max(0.0, min(1.0, self.shield_remaining[1] / SHIELD_MAX_SECONDS))
        self._draw_shield_bar(x2, top_y + in_h + 6, bar_w, sh_h, shield_frac2, broken=self.guard_broken[1])
        health_frac2 = max(0.0, min(1.0, self.health[1] / HEALTH_MAX))
        self._draw_health_bar(x2, top_y + in_h + 6 + sh_h + 6, bar_w, hp_h, health_frac2)

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

    def _draw_health_bar(self, x: int, y: int, w: int, h: int, frac: float):
        # Background
        pygame.draw.rect(self.scene, (30, 30, 36), (x, y, w, h), border_radius=4)
        # Fill (use ACCENT to differentiate from shield/FG)
        fill_w = int(max(0, min(w, round(w * frac))))
        col = (120, 220, 100)  # a greenish health color
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
