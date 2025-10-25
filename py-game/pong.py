#!/usr/bin/python3
"""
Simple two-player Pong with alien spaceships and pluggable Bluetooth input hooks.

Controls
- Player 1 (left paddle): W/S
- Player 2 (right paddle): Up/Down arrows

Bluetooth
- Template methods `poll_ble_player1()` and `poll_ble_player2()` return an int:
  -1 = up, 0 = no input, +1 = down. Replace their bodies with your BLE polling
  logic (e.g., using bleak). If a BLE poll returns non-zero, it takes priority
  over keyboard input for that player on that frame.

Run
  python3 py-game/pong.py

If pygame is missing, install it: pip install pygame
"""

from __future__ import annotations

import math
import os
import sys

try:
	import pygame
except Exception as e:  # pragma: no cover - runtime check for friendly error
	print("pygame is required to run this game.\nInstall with: pip install pygame", file=sys.stderr)
	raise


# ------------------------------- Config ------------------------------------
WIDTH, HEIGHT = 960, 540
FPS = 75

SHIP_W, SHIP_H = 104, 364
SHIP_MARGIN = 30
SHIP_SPEED = 420.0  # pixels per second

ASTEROID_SPEED = 360.0
ASTEROID_SPEED_INCREMENT = 14.0  # increase after each paddle hit
ASTEROID_MAX_ANGLE_DEG = 48

SCORE_TO_WIN = 7

BG_COLOR = (12, 12, 16)
FG_COLOR = (235, 235, 245)
ACCENT = (80, 200, 120)

# Dome positioning (tweakable)
# How far to place the dome outside the top oval horizontally (in fractions of the top oval width)
DOME_OUTSIDE_OFFSET_FRAC = 0.0
# Vertical adjustment relative to the top oval center (fraction of the top oval height, positive = down, negative = up)
DOME_VERTICAL_OFFSET_FRAC = 0.0

# Asteroid sprite bounding box (ball image size)
ASTEROID_W, ASTEROID_H = 50, 50

# Ship collision box controls
# - mode "box": use full SHIP_W × SHIP_H
# - mode "content": use the actual scaled sprite area (ignores letterbox padding)
SHIP_COLLISION_MODE = "content"  # "box" or "content"
SHIP_COLLISION_INFLATE = 0        # inflate (+) or deflate (-) the collision rect (applied to width and height)


# ------------------------------- Game --------------------------------------
from controls import ControlsMixin
from sprites import Ship, Ball


class Game(ControlsMixin):
	def __init__(self):
		pygame.init()
		pygame.display.set_caption("Space Cowboy Pong")
		self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
		self.clock = pygame.time.Clock()
		self.font = pygame.font.SysFont("monospace", 24)
		self.big_font = pygame.font.SysFont("monospace", 56)

		self.left = Ship(
			SHIP_MARGIN, HEIGHT // 2 - SHIP_H // 2, SHIP_W, SHIP_H, HEIGHT,
			collision_mode=SHIP_COLLISION_MODE, collision_inflate=SHIP_COLLISION_INFLATE,
		)
		self.right = Ship(
			WIDTH - SHIP_MARGIN - SHIP_W, HEIGHT // 2 - SHIP_H // 2, SHIP_W, SHIP_H, HEIGHT,
			collision_mode=SHIP_COLLISION_MODE, collision_inflate=SHIP_COLLISION_INFLATE,
		)
		# Ball uses an image; scale controlled by ASTEROID_W/H
		self.ball = Ball(0, 0, ASTEROID_W, ASTEROID_H, ASTEROID_SPEED, 0.0)

		self.score = [0, 0]
		self.running = True
		self.game_over = False
		self.winner: int | None = None  # 0 for left, 1 for right

	# --------------------------- Physics & Rules --------------------------
	def update(self, dt: float):
		d1, d2 = self.input_dirs()
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
		lrect = self.left.rect()
		rrect = self.right.rect()

		if ball_rect.colliderect(lrect) and self.ball.vx < 0:
			self._reflect_from_ship(self.left)
		elif ball_rect.colliderect(rrect) and self.ball.vx > 0:
			self._reflect_from_ship(self.right)

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

	def _reflect_from_ship(self, ship: Ship):
		# Compute hit position relative to ship center to set outgoing angle
		ship_center = ship.y + ship.h / 2
		rel = (self.ball.y + self.ball.h / 2) - ship_center
		norm = max(-1.0, min(1.0, (2.0 * rel) / ship.h))
		angle = math.radians(norm * ASTEROID_MAX_ANGLE_DEG)

		speed = math.hypot(self.ball.vx, self.ball.vy) + ASTEROID_SPEED_INCREMENT
		direction = 1 if ship is self.left else -1
		self.ball.vx = direction * speed * math.cos(angle)
		self.ball.vy = speed * math.sin(angle)

		# Nudge ball outside paddle to avoid sticking
		if direction > 0:
			self.ball.x = self.left.x + self.left.w
		else:
			self.ball.x = self.right.x - self.ball.w

	# --------------------------- Rendering --------------------------------
	def draw(self):
		self.screen.fill(BG_COLOR)

		# Center dashed line
		dash_h = 10
		gap = 10
		x = WIDTH // 2 - 1
		for y in range(0, HEIGHT, dash_h + gap):
			pygame.draw.rect(self.screen, (40, 40, 48), pygame.Rect(x, y, 2, dash_h))

		# Ships and ball
		self.left.draw(self.screen, facing_right=True, fg_color=FG_COLOR, accent=ACCENT,
					  dome_outside_offset_frac=DOME_OUTSIDE_OFFSET_FRAC,
					  dome_vertical_offset_frac=DOME_VERTICAL_OFFSET_FRAC)
		self.right.draw(self.screen, facing_right=False, fg_color=FG_COLOR, accent=ACCENT,
					   dome_outside_offset_frac=DOME_OUTSIDE_OFFSET_FRAC,
					   dome_vertical_offset_frac=DOME_VERTICAL_OFFSET_FRAC)
		self.ball.draw(self.screen)

		# Scoreboard
		score_text = f"{self.score[0]}   {self.score[1]}"
		surf = self.font.render(score_text, True, FG_COLOR)
		self.screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, 16))

		# End-of-game banner overlay
		if self.game_over:
			overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
			overlay.fill((0, 0, 0, 140))  # semi-transparent dark layer
			self.screen.blit(overlay, (0, 0))

			winner_text = "Player 1 Wins!" if self.winner == 0 else "Player 2 Wins!"
			win_surf = self.big_font.render(winner_text, True, FG_COLOR)
			self.screen.blit(win_surf, (WIDTH // 2 - win_surf.get_width() // 2, HEIGHT // 2 - 60))

			prompt1 = "Press R to restart"
			prompt2 = "Press Q to quit"
			p1 = self.font.render(prompt1, True, FG_COLOR)
			p2 = self.font.render(prompt2, True, FG_COLOR)
			self.screen.blit(p1, (WIDTH // 2 - p1.get_width() // 2, HEIGHT // 2 + 8))
			self.screen.blit(p2, (WIDTH // 2 - p2.get_width() // 2, HEIGHT // 2 + 36))

		pygame.display.flip()

	def restart(self):
		# Reset game state for a new match
		self.score = [0, 0]
		self.left.y = HEIGHT // 2 - SHIP_H // 2
		self.right.y = HEIGHT // 2 - SHIP_H // 2
		self.ball.reset(WIDTH, HEIGHT, direction=1)
		self.ball.vx = ASTEROID_SPEED
		self.ball.vy = 0.0
		self.game_over = False
		self.winner = None

	# --------------------------- Main loop --------------------------------
	def run(self):
		self.ball.reset(WIDTH, HEIGHT, direction=1)
		self.ball.vx = ASTEROID_SPEED
		self.ball.vy = 0.0
		while self.running:
			dt = self.clock.tick(FPS) / 1000.0
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					self.running = False
				elif event.type == pygame.KEYDOWN:
					if event.key in (pygame.K_ESCAPE, pygame.K_q):
						self.running = False
					elif event.key == pygame.K_r:
						self.restart()

			if not self.game_over:
				self.update(dt)
			self.draw()

		pygame.quit()
		

if __name__ == "__main__":
	Game().run()