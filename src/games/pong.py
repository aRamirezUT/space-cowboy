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


import math
import random
import pygame

from src.games.base_game import BaseGame
from src.controls.controls import Controls
from src.sprites.player import Player
from src.sprites.Asteroid import Asteroid
from src.sprites.background import render_starfield_surface
from src.configs.pong import (
    BASE_WIDTH, BASE_HEIGHT, WINDOW_SCALE,
    FPS,
    SHIP_SIZE_FRAC, SHIP_MARGIN_FRAC, SHIP_SPEED_FRAC,
    ASTEROID_SPEED_FRAC, ASTEROID_SIZE_FRAC, ASTEROID_SPEED_INCREMENT, ASTEROID_MAX_ANGLE_DEG,
    SCORE_TO_WIN,
    BG_COLOR, FG_COLOR,
    SHIP_FRONT_HITBOX_FRAC,
    STAR_DENSITY, STAR_SIZE_MIN, STAR_SIZE_MAX,
    FONT_PATH, IMG_NAME,
    CENTER_LINE_COLOR, OVERLAY_ALPHA, DASH_HEIGHT, DASH_GAP, CENTER_LINE_WIDTH,
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


class Pong(BaseGame):
    def __init__(
        self,
        controls: Controls,
        screen: pygame.Surface,
    ) -> None:
        super().__init__(screen, font_path=FONT_PATH, width=WIDTH, height=HEIGHT)

        pygame.display.set_caption("MYO BEBOP Pong")
        self.controls = controls
        self.scene = pygame.Surface((WIDTH, HEIGHT))  # Override base class scene with correct size
        self.clock = pygame.time.Clock()
        self.render_background()
        
        self.left = Player(
            x=SHIP_MARGIN, y=HEIGHT // 2 - SHIP_H // 2, 
            w=SHIP_W, h=SHIP_H, world_height=HEIGHT, image_name=IMG_NAME
        )
        self.right = Player(
            x=WIDTH - SHIP_MARGIN - SHIP_W, y=HEIGHT // 2 - SHIP_H // 2, 
            w=SHIP_W, h=SHIP_H, world_height=HEIGHT, image_name=IMG_NAME
        )
        # Asteroid uses an image; start stationary centered until user starts
        self.ball = Asteroid(
            x=0, y=0, w=ASTEROID_W, h=ASTEROID_H, vx=0.0, vy=0.0
        )
        self.ball.reset(WIDTH, HEIGHT)

        self.waiting_for_start = True
        self.score = [0, 0]
        self.game_over = False
        self.winner: int | None = None  # 0 for left, 1 for right

    # --------------------------- Physics & Rules --------------------------
    def _update(self, dt: float):
        keys = pygame.key.get_pressed()
        d1, d2 = self.controls.get_inputs(keys)
        
        # Move players: 0 = down (+1), 1 = up (-1)
        d1 = -1 if d1 >= 0.5 else 1
        d2 = -1 if d2 >= 0.5 else 1
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

        # Player collisions
        ball_rect: pygame.Rect = self.ball.rect()
        lrect: pygame.Rect = self._player_front_hitbox(self.left, facing_right=True)
        rrect: pygame.Rect = self._player_front_hitbox(self.right, facing_right=False)
        
        # Ball collisions
        if ball_rect.colliderect(lrect) and self.ball.vx < 0:
            self._reflect_from_player(self.left, facing_right=True, rect_hitbox=lrect)
        elif ball_rect.colliderect(rrect) and self.ball.vx > 0:
            self._reflect_from_player(self.right, facing_right=False, rect_hitbox=rrect)

        # Scoring
        if self.ball.x + self.ball.w < 0:  # missed left
            self._handle_score(player=1, ball_direction=-1)
        elif self.ball.x > WIDTH:  # missed right
            self._handle_score(player=0, ball_direction=1)

    def _reflect_from_player(self, player: Player, facing_right: bool, rect_hitbox: pygame.Rect):
        # Compute hit position relative to player center to set outgoing angle
        player_center = player.y + player.h / 2
        rel = (self.ball.y + self.ball.h / 2) - player_center
        norm = max(-1.0, min(1.0, (2.0 * rel) / player.h))
        angle = math.radians(norm * ASTEROID_MAX_ANGLE_DEG)

        speed = math.hypot(self.ball.vx, self.ball.vy) + ASTEROID_SPEED_INCREMENT
        direction = 1 if player is self.left else -1
        self.ball.vx = direction * speed * math.cos(angle)
        self.ball.vy = speed * math.sin(angle)

        # Nudge ball just outside the player's front face to avoid repeated/behind collisions
        # Left player: front face is the right edge of hitbox
        # Right player: front face is the left edge of hitbox
        self.ball.x = rect_hitbox.right if facing_right else rect_hitbox.left - self.ball.w

        # Keep ball within vertical bounds after correction (defensive)
        self.ball.y = max(0, min(HEIGHT - self.ball.h, self.ball.y))

    def _player_front_hitbox(self, player: Player, *, facing_right: bool) -> pygame.Rect:
        # Base rectangle as defined by player's collision settings
        base = player.rect()
        front_w = max(1, int(round(base.w * SHIP_FRONT_HITBOX_FRAC)))
        if facing_right:
            # Rightmost slice
            return pygame.Rect(base.right - front_w, base.top, front_w, base.h)
        else:
            # Leftmost slice
            return pygame.Rect(base.left, base.top, front_w, base.h)

    # --------------------------- Rendering --------------------------------
    def _render(self):
        # Draw to the offscreen scene in world coordinates
        if self._bg_prepared is not None:
            self.scene.blit(self._bg_prepared, (0, 0))
        else:
            self.scene.fill(BG_COLOR)

        # Center dashed line
        self._draw_center_line()

        # Ships and ball
        self.left.draw(self.scene, facing_right=True)
        self.right.draw(self.scene, facing_right=False)
        self.ball.draw(self.scene)

        # Scoreboard
        score_text = f"{self.score[0]}   {self.score[1]}"
        surf = self.small_font.render(score_text, True, FG_COLOR)
        self.scene.blit(surf, (WIDTH // 2 - surf.get_width() // 2, 16))

        # End-of-game banner overlay
        if self.game_over:
            self.scene.blit(super().create_overlay(alpha = OVERLAY_ALPHA), (0, 0))
            winner_text = "Player 1 Wins!" if self.winner == 0 else "Player 2 Wins!"
            super().render_centered_text(winner_text, self.big_font, FG_COLOR, -60)
            super().render_centered_text("Press R to restart", self.small_font, FG_COLOR, 8)
            super().render_centered_text("Press Q to quit", self.small_font, FG_COLOR, 36)

        # Start-screen overlay
        if self.waiting_for_start and not self.game_over:
            self.scene.blit(super().create_overlay(alpha = OVERLAY_ALPHA), (0, 0))
            super().render_centered_text("MYO BEBOP Pong", self.big_font, FG_COLOR, -60)
            super().render_centered_text("Press SPACE or ENTER to start", self.small_font, FG_COLOR, 8)

        # Scale the scene to the current window size and present
        display_size = self.screen.get_size()
        scaled = pygame.transform.smoothscale(self.scene, display_size)
        self.screen.blit(scaled, (0, 0))
        pygame.display.flip()

    def render_background(self):
        """Generate and cache the world-sized starfield background via sprites.background."""
        self._bg_prepared = render_starfield_surface(
            WIDTH,
            HEIGHT,
            density=STAR_DENSITY,
            size_min=STAR_SIZE_MIN,
            size_max=STAR_SIZE_MAX,
            bg_color=(0, 0, 0),
        )
    
    def _reset_ball_after_score(self, direction: int) -> None:
        """Reset ball position and velocity after a score."""
        self.ball.reset(WIDTH, HEIGHT)
        self.ball.vx = direction * ASTEROID_SPEED
        self.ball.vy = 0.0
    
    def _handle_score(self, player: int, ball_direction: int) -> None:
        """Handle scoring logic for a player."""
        self.score[player] += 1
        if self.score[player] >= SCORE_TO_WIN:
            self.game_over = True
            self.winner = player
        else:
            self._reset_ball_after_score(ball_direction)
    
    def _draw_center_line(self) -> None:
        """Draw the dashed center line."""
        x = WIDTH // 2 - CENTER_LINE_WIDTH // 2
        for y in range(0, HEIGHT, DASH_HEIGHT + DASH_GAP):
            pygame.draw.rect(self.scene, CENTER_LINE_COLOR, pygame.Rect(x, y, CENTER_LINE_WIDTH, DASH_HEIGHT))
    
    def _start_game(self) -> None:
        """Start the game with random ball direction."""
        self.waiting_for_start = False
        self.ball.reset(WIDTH, HEIGHT)
        # Randomize initial horizontal direction: left or right
        dir_sign = random.choice((-1, 1))
        self.ball.vx = dir_sign * ASTEROID_SPEED
        self.ball.vy = 0.0

    def restart(self):
        # Reset game state for a new match
        self.score = [0, 0]
        self.left.y = HEIGHT // 2 - SHIP_H // 2
        self.right.y = HEIGHT // 2 - SHIP_H // 2
        self.ball.reset(WIDTH, HEIGHT)
        self.ball.vx = 0.0
        self.ball.vy = 0.0
        self.game_over = False
        self.winner = None
        self.waiting_for_start = True
        # Regenerate a fresh starfield for each restart for variety
        self.render_background()

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                self.handle_menu_events(event)
            if not self.game_over and not self.waiting_for_start:
                self._update(dt)
            self._render()

    def handle_menu_events(self, event: pygame.event.Event) -> None:
        super().handle_menu_events(event)
        if event.type == pygame.KEYDOWN:
            if self.waiting_for_start and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self._start_game()
