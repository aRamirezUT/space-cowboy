#!/usr/bin/python3
"""
Simple two-player Pong with alien spaceships and pluggable Bluetooth input hooks.

Controls
- Player 1 (left paddle): W/S
- Player 2 (right paddle): Up/Down arrows

Bluetooth
- Template methods `poll_ble()` return a tuple[int, int]:
  -1 = up, 0 = no input, +1 = down. Replace their bodies with your BLE polling
  logic (e.g., using bleak). If a BLE poll returns non-zero, it takes priority
  over keyboard input for that player on that frame.

Run
  python3 py-game/pong.py

If pygame is missing, install it: pip install pygame
"""

from __future__ import annotations

import math
import random
import pygame

from .controls import Controls
from .sprites import Ship, Ball
from .sprites.background import make_starfield_surface

from .configs.pong import (
    BASE_WIDTH, BASE_HEIGHT, WINDOW_SCALE,
    FPS,
    SHIP_SIZE_FRAC, SHIP_MARGIN_FRAC, SHIP_SPEED_FRAC,
    ASTEROID_SPEED_FRAC, ASTEROID_SIZE_FRAC, ASTEROID_SPEED_INCREMENT, ASTEROID_MAX_ANGLE_DEG,
    SCORE_TO_WIN,
    BG_COLOR, FG_COLOR, ACCENT,
    DOME_OUTSIDE_OFFSET_FRAC, DOME_VERTICAL_OFFSET_FRAC,
    SHIP_COLLISION_MODE, SHIP_COLLISION_INFLATE,
    SHIP_FRONT_HITBOX_FRAC,
    STAR_DENSITY, STAR_SIZE_MIN, STAR_SIZE_MAX,
    FONT_PATH,
)

# Logical world size (fixed) and initial display size
WIDTH, HEIGHT = BASE_WIDTH, BASE_HEIGHT  # world coordinates
INITIAL_DISPLAY_SIZE = (int(BASE_WIDTH * WINDOW_SCALE), int(BASE_HEIGHT * WINDOW_SCALE))

# Derived pixel values from scalers
SHIP_W = SHIP_H = max(1, int(round(HEIGHT * SHIP_SIZE_FRAC)))
SHIP_MARGIN = max(1, int(round(WIDTH * SHIP_MARGIN_FRAC)))
SHIP_SPEED = HEIGHT * SHIP_SPEED_FRAC  # pixels per second

ASTEROID_W = ASTEROID_H = max(1, int(round(HEIGHT * ASTEROID_SIZE_FRAC)))
ASTEROID_SPEED = HEIGHT * ASTEROID_SPEED_FRAC


# ------------------------------- Game --------------------------------------
class Game():
    def __init__(self, *, controls:Controls, screen: 'pygame.Surface | None' = None, own_display: 'bool | None' = None):
        super().__init__()
        pygame.init()
        pygame.display.set_caption("MYO BEBOP Pong")
        self._owns_display = bool(own_display) if own_display is not None else (screen is None)
        # Start in fullscreen by default only when we own the display
        if self._owns_display:
            self.screen = pygame.display.set_mode((0, 0), pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.FULLSCREEN)
            self.fullscreen = True
        else:
            self.screen = screen  # type: ignore[assignment]
            self.fullscreen = False
        self.controls = controls
        # Offscreen scene rendered at world resolution; scaled to window each frame
        self.scene = pygame.Surface((WIDTH, HEIGHT))
        # Prepared background surface (scaled to world size), or None for solid fill
        self._bg_prepared = None
        self.clock = pygame.time.Clock()
        # Load shared game fonts (small used for UI, big for titles)
        try:
            from .fonts.fonts import load_fonts
            f = load_fonts(small=24, medium=40, big=56, font_path=FONT_PATH)
            self.font = f.small
            self.big_font = f.big
        except Exception:
            # Fallback to system fonts if loader not available
            self.font = pygame.font.SysFont("monospace", 24)
            self.big_font = pygame.font.SysFont("monospace", 56)

        self._prepare_background()

        # Start screen state: don't begin gameplay until user starts
        self.waiting_for_start = True

        self.left = Ship(
            SHIP_MARGIN, HEIGHT // 2 - SHIP_H // 2, SHIP_W, SHIP_H, HEIGHT,
            collision_mode=SHIP_COLLISION_MODE, collision_inflate=SHIP_COLLISION_INFLATE,
        )
        self.right = Ship(
            WIDTH - SHIP_MARGIN - SHIP_W, HEIGHT // 2 - SHIP_H // 2, SHIP_W, SHIP_H, HEIGHT,
            collision_mode=SHIP_COLLISION_MODE, collision_inflate=SHIP_COLLISION_INFLATE,
        )
        # Ball uses an image; start stationary centered until user starts
        self.ball = Ball(0, 0, ASTEROID_W, ASTEROID_H, 0.0, 0.0)
        self.ball.reset(WIDTH, HEIGHT, direction=1)

        self.score = [0, 0]
        self.running = True
        self.game_over = False
        self.winner: int | None = None  # 0 for left, 1 for right

    # --------------------------- Physics & Rules --------------------------
    def update(self, dt: float):
        d1, d2 = self.controls.get_data()
        
        d1 = 1 if d1 < 0.5 else (-1 if d1 > 0.5 else 0)
        d2 = 1 if d2 < 0.5 else (-1 if d2 > 0.5 else 0)
        self.left.move(d1 * SHIP_SPEED * dt)
        self.right.move(d2 * SHIP_SPEED * dt)

        # Move ball
        self.ball.x += self.ball.vx * dt
        self.ball.y += self.ball.vy * dt

        # Top/bottom wall bounce
        if self.ball.y <= 0:
            self.ball.y = 0
            self.ball.vy = abs(self.ball.vy)
        elif self.ball.y + self.ball.h >= HEIGHT:
            self.ball.y = HEIGHT - self.ball.h
            self.ball.vy = -abs(self.ball.vy)

        # Ship collisions
        ball_rect = self.ball.rect()
        lrect = self._ship_front_hitbox(self.left, facing_right=True)
        rrect = self._ship_front_hitbox(self.right, facing_right=False)

        # Only reflect when approaching the ship's front face and overlapping its front hitbox
        if ball_rect.colliderect(lrect) and self.ball.vx < 0:
            self._reflect_from_ship(self.left, facing_right=True, hitbox=lrect)
        elif ball_rect.colliderect(rrect) and self.ball.vx > 0:
            self._reflect_from_ship(self.right, facing_right=False, hitbox=rrect)

        # Scoring
        if self.ball.x + self.ball.w < 0:  # missed left
            self.score[1] += 1
            if self.score[1] >= SCORE_TO_WIN:
                self.game_over = True
                self.winner = 1
            else:
                self.ball.reset(WIDTH, HEIGHT, direction=-1)
                self.ball.vx = -ASTEROID_SPEED
                self.ball.vy = 0.0
        elif self.ball.x > WIDTH:  # missed right
            self.score[0] += 1
            if self.score[0] >= SCORE_TO_WIN:
                self.game_over = True
                self.winner = 0
            else:
                self.ball.reset(WIDTH, HEIGHT, direction=1)
                self.ball.vx = ASTEROID_SPEED
                self.ball.vy = 0.0

    def _reflect_from_ship(self, ship: Ship, *, facing_right: bool, hitbox):
        # Compute hit position relative to ship center to set outgoing angle
        ship_center = ship.y + ship.h / 2
        rel = (self.ball.y + self.ball.h / 2) - ship_center
        norm = max(-1.0, min(1.0, (2.0 * rel) / ship.h))
        angle = math.radians(norm * ASTEROID_MAX_ANGLE_DEG)

        speed = math.hypot(self.ball.vx, self.ball.vy) + ASTEROID_SPEED_INCREMENT
        direction = 1 if ship is self.left else -1
        self.ball.vx = direction * speed * math.cos(angle)
        self.ball.vy = speed * math.sin(angle)

        # Nudge ball just outside the ship's front face to avoid repeated/behind collisions
        if facing_right:
            # Left ship: front face is the right edge of hitbox
            self.ball.x = hitbox.right
        else:
            # Right ship: front face is the left edge of hitbox
            self.ball.x = hitbox.left - self.ball.w

        # Keep ball within vertical bounds after correction (defensive)
        self.ball.y = max(0, min(HEIGHT - self.ball.h, self.ball.y))

    def _ship_front_hitbox(self, ship: Ship, *, facing_right: bool):
        # Base rectangle as defined by ship's collision settings
        base = ship.rect()
        front_w = max(1, int(round(base.w * SHIP_FRONT_HITBOX_FRAC)))
        if facing_right:
            # Rightmost slice
            return pygame.Rect(base.right - front_w, base.top, front_w, base.h)
        else:
            # Leftmost slice
            return pygame.Rect(base.left, base.top, front_w, base.h)

    # --------------------------- Rendering --------------------------------
    def draw(self):
        # Draw to the offscreen scene in world coordinates
        if self._bg_prepared is not None:
            self.scene.blit(self._bg_prepared, (0, 0))
        else:
            self.scene.fill(BG_COLOR)

        # Center dashed line
        dash_h = 10
        gap = 10
        x = WIDTH // 2 - 1
        for y in range(0, HEIGHT, dash_h + gap):
            pygame.draw.rect(self.scene, (40, 40, 48), pygame.Rect(x, y, 2, dash_h))

        # Ships and ball
        self.left.draw(self.scene, facing_right=True, fg_color=FG_COLOR, accent=ACCENT,
                      dome_outside_offset_frac=DOME_OUTSIDE_OFFSET_FRAC,
                      dome_vertical_offset_frac=DOME_VERTICAL_OFFSET_FRAC)
        self.right.draw(self.scene, facing_right=False, fg_color=FG_COLOR, accent=ACCENT,
                       dome_outside_offset_frac=DOME_OUTSIDE_OFFSET_FRAC,
                       dome_vertical_offset_frac=DOME_VERTICAL_OFFSET_FRAC)
        self.ball.draw(self.scene)

        # Scoreboard
        score_text = f"{self.score[0]}   {self.score[1]}"
        surf = self.font.render(score_text, True, FG_COLOR)
        self.scene.blit(surf, (WIDTH // 2 - surf.get_width() // 2, 16))

        # End-of-game banner overlay
        if self.game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))  # semi-transparent dark layer
            self.scene.blit(overlay, (0, 0))

            winner_text = "Player 1 Wins!" if self.winner == 0 else "Player 2 Wins!"
            win_surf = self.big_font.render(winner_text, True, FG_COLOR)
            self.scene.blit(win_surf, (WIDTH // 2 - win_surf.get_width() // 2, HEIGHT // 2 - 60))

            prompt1 = "Press R to restart"
            prompt2 = "Press Q to quit"
            p1 = self.font.render(prompt1, True, FG_COLOR)
            p2 = self.font.render(prompt2, True, FG_COLOR)
            self.scene.blit(p1, (WIDTH // 2 - p1.get_width() // 2, HEIGHT // 2 + 8))
            self.scene.blit(p2, (WIDTH // 2 - p2.get_width() // 2, HEIGHT // 2 + 36))

        # Start-screen overlay
        if self.waiting_for_start and not self.game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            self.scene.blit(overlay, (0, 0))
            title = self.big_font.render("MYO BEBOP Pong", True, FG_COLOR)
            prompt = self.font.render("Press SPACE or ENTER to start", True, FG_COLOR)
            self.scene.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 60))
            self.scene.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, HEIGHT // 2 + 8))

        # Scale the scene to the current window size and present
        display_size = self.screen.get_size()
        scaled = pygame.transform.smoothscale(self.scene, display_size)
        self.screen.blit(scaled, (0, 0))
        pygame.display.flip()

    def _prepare_background(self):
        """Generate and cache the world-sized starfield background via sprites.background."""
        self._bg_prepared = make_starfield_surface(
            WIDTH,
            HEIGHT,
            density=STAR_DENSITY,
            size_min=STAR_SIZE_MIN,
            size_max=STAR_SIZE_MAX,
            bg_color=(0, 0, 0),
        )

    def restart(self):
        # Reset game state for a new match
        self.score = [0, 0]
        self.left.y = HEIGHT // 2 - SHIP_H // 2
        self.right.y = HEIGHT // 2 - SHIP_H // 2
        self.ball.reset(WIDTH, HEIGHT, direction=1)
        self.ball.vx = 0.0
        self.ball.vy = 0.0
        self.game_over = False
        self.winner = None
        self.waiting_for_start = True
        # Regenerate a fresh starfield for each restart for variety
        self._prepare_background()

    # --------------------------- Main loop --------------------------------
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    # Recreate the display surface with the new size
                    if not getattr(self, 'fullscreen', False):
                        self.screen = pygame.display.set_mode(event.size, pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        self.running = False
                    elif event.key == pygame.K_r:
                        self.restart()
                    elif event.key == pygame.K_F11:
                        # Toggle fullscreen
                        if getattr(self, 'fullscreen', False):
                            self.screen = pygame.display.set_mode(INITIAL_DISPLAY_SIZE, pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)
                            self.fullscreen = False
                        else:
                            self.screen = pygame.display.set_mode((0, 0), pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.FULLSCREEN)
                            self.fullscreen = True
                    elif self.waiting_for_start and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        # Start gameplay
                        self.waiting_for_start = False
                        self.ball.reset(WIDTH, HEIGHT, direction=1)
                        # Randomize initial horizontal direction: left or right
                        dir_sign = random.choice((-1, 1))
                        self.ball.vx = dir_sign * ASTEROID_SPEED
                        self.ball.vy = 0.0

            if not self.game_over and not self.waiting_for_start:
                self.update(dt)
            self.draw()

        if getattr(self, '_owns_display', True):
            pygame.quit()
        

if __name__ == "__main__":
    Game().run()