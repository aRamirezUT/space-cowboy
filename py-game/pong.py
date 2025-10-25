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
from dataclasses import dataclass
from typing import Tuple

try:
	import pygame
except Exception as e:  # pragma: no cover - runtime check for friendly error
	print("pygame is required to run this game.\nInstall with: pip install pygame", file=sys.stderr)
	raise


# ------------------------------- Config ------------------------------------
WIDTH, HEIGHT = 960, 540
FPS = 75

SHIP_W, SHIP_H = 26, 96
SHIP_MARGIN = 30
SHIP_SPEED = 420.0  # pixels per second

BALL_SIZE = 14
BALL_SPEED = 360.0
BALL_SPEED_INCREMENT = 14.0  # increase after each paddle hit
BALL_MAX_ANGLE_DEG = 48

SCORE_TO_WIN = 7

BG_COLOR = (12, 12, 16)
FG_COLOR = (235, 235, 245)
ACCENT = (80, 200, 120)

# Dome positioning (tweakable)
# How far to place the dome outside the top oval horizontally (in fractions of the top oval width)
DOME_OUTSIDE_OFFSET_FRAC = 0.0
# Vertical adjustment relative to the top oval center (fraction of the top oval height, positive = down, negative = up)
DOME_VERTICAL_OFFSET_FRAC = 0.0


# ------------------------------- Input -------------------------------------
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
	# TODO: Replace with real BLE polling. Keep non-blocking per-frame.
	return 0, 0

# ------------------------------- Game --------------------------------------
@dataclass
class Ship:
	x: int
	y: int
	w: int = SHIP_W
	h: int = SHIP_H

	def rect(self) -> pygame.Rect:
		return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

	def move(self, dy: float):
		self.y += dy
		self.y = max(0, min(HEIGHT - self.h, self.y))

	def draw_ship(self, surface: pygame.Surface, facing_right: bool):
		# Draw a UFO with two ovals stacked horizontally with overlap and a raised dome.
		x, y, w, h = self.x, self.y, self.w, self.h

		# Sizes
		base_w = max(6, int(w * 0.72))
		top_w = max(4, int(w * 0.62))
		base_h = max(6, int(h * 0.82))
		top_h = max(4, int(h * 0.52))
		# Overlap the ovals horizontally by a fraction of the smaller width
		overlap = int(min(base_w, top_w) * 0.35)
		gap = -overlap

		# Vertical alignment: center both ovals vertically in ship bounds
		cy = y + h // 2
		base_y = cy - base_h // 2
		top_y = cy - top_h // 2

		# Horizontal stacking: order depends on facing_right
		pair_w = base_w + gap + top_w
		start_x = x + (w - pair_w) // 2
		if facing_right:
			# Left player: stack to the right (base first, then top overlapping to the right)
			base_x = start_x
			top_x = base_x + base_w + gap
		else:
			# Right player: stack to the left (top first, then base overlapping to the right)
			top_x = start_x
			base_x = top_x + top_w + gap

		base_rect = pygame.Rect(base_x, base_y, base_w, base_h)
		top_rect = pygame.Rect(top_x, top_y, top_w, top_h)
		pygame.draw.ellipse(surface, FG_COLOR, base_rect)
		pygame.draw.ellipse(surface, FG_COLOR, top_rect)

		# Dome positioned horizontally outside the top oval
		dome_r = max(3, int(min(top_h, top_w, base_h, base_w) * 0.55))
		outside_offset = int(top_w * DOME_OUTSIDE_OFFSET_FRAC)
		if facing_right:
			# Place to the right of the top oval
			dome_cx = top_rect.right + dome_r + outside_offset
		else:
			# Place to the left of the top oval
			dome_cx = top_rect.left - dome_r - outside_offset
		# Vertical position relative to top oval center
		dome_cy = top_rect.centery + int(top_h * DOME_VERTICAL_OFFSET_FRAC)
		pygame.draw.circle(surface, ACCENT, (dome_cx, dome_cy), dome_r)

		# Subtle highlight
		hl_r = max(1, dome_r // 2)
		hl_x = min(WIDTH - 1, dome_cx - dome_r // 3)
		hl_y = max(0, dome_cy - dome_r // 3)
		hl_color = (
			min(255, ACCENT[0] + 20),
			min(255, ACCENT[1] + 20),
			min(255, ACCENT[2] + 20),
		)
		pygame.draw.circle(surface, hl_color, (hl_x, hl_y), hl_r)


@dataclass
class Ball:
	x: float
	y: float
	size: int = BALL_SIZE
	vx: float = BALL_SPEED
	vy: float = 0.0

	def rect(self) -> pygame.Rect:
		return pygame.Rect(int(self.x), int(self.y), self.size, self.size)

	def reset(self, direction: int = 1):
		self.x = WIDTH // 2 - self.size // 2
		self.y = HEIGHT // 2 - self.size // 2
		self.vx = direction * BALL_SPEED
		self.vy = 0.0


class Game:
	def __init__(self):
		pygame.init()
		pygame.display.set_caption("Space Cowboy Pong")
		self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
		self.clock = pygame.time.Clock()
		self.font = pygame.font.SysFont("monospace", 24)

		self.left = Ship(SHIP_MARGIN, HEIGHT // 2 - SHIP_H // 2)
		self.right = Ship(WIDTH - SHIP_MARGIN - SHIP_W, HEIGHT // 2 - SHIP_H // 2)
		self.ball = Ball(WIDTH // 2 - BALL_SIZE // 2, HEIGHT // 2 - BALL_SIZE // 2)

		self.score = [0, 0]
		self.running = True

	# --------------------------- Input handling ---------------------------
	@staticmethod
	def keyboard_dir_for_player1(keys: pygame.key.ScancodeWrapper) -> int:
		up = keys[pygame.K_w]
		down = keys[pygame.K_s]
		return (-1 if up and not down else 1 if down and not up else 0)

	@staticmethod
	def keyboard_dir_for_player2(keys: pygame.key.ScancodeWrapper) -> int:
		up = keys[pygame.K_UP]
		down = keys[pygame.K_DOWN]
		return (-1 if up and not down else 1 if down and not up else 0)

	def input_dirs(self) -> Tuple[int, int]:
		keys = pygame.key.get_pressed()
		kb1 = self.keyboard_dir_for_player1(keys)
		kb2 = self.keyboard_dir_for_player2(keys)
		ble1, ble2 = poll_ble()

		# Prioritize BLE when non-zero; otherwise use keyboard
		d1 = ble1 if ble1 != 0 else kb1
		d2 = ble2 if ble2 != 0 else kb2
		return d1, d2

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
		elif self.ball.y + self.ball.size >= HEIGHT:
			self.ball.y = HEIGHT - self.ball.size
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
		if self.ball.x + self.ball.size < 0:  # missed left
			self.score[1] += 1
			self.ball.reset(direction=-1)
		elif self.ball.x > WIDTH:  # missed right
			self.score[0] += 1
			self.ball.reset(direction=1)

	def _reflect_from_ship(self, ship: Ship):
		# Compute hit position relative to ship center to set outgoing angle
		ship_center = ship.y + ship.h / 2
		rel = (self.ball.y + self.ball.size / 2) - ship_center
		norm = max(-1.0, min(1.0, (2.0 * rel) / ship.h))
		angle = math.radians(norm * BALL_MAX_ANGLE_DEG)

		speed = math.hypot(self.ball.vx, self.ball.vy) + BALL_SPEED_INCREMENT
		direction = 1 if ship is self.left else -1
		self.ball.vx = direction * speed * math.cos(angle)
		self.ball.vy = speed * math.sin(angle)

		# Nudge ball outside paddle to avoid sticking
		if direction > 0:
			self.ball.x = self.left.x + self.left.w
		else:
			self.ball.x = self.right.x - self.ball.size

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
		self.left.draw_ship(self.screen, facing_right=True)
		self.right.draw_ship(self.screen, facing_right=False)
		pygame.draw.rect(self.screen, ACCENT, self.ball.rect(), border_radius=4)

		# Score
		score_text = f"{self.score[0]}   {self.score[1]}"
		surf = self.font.render(score_text, True, FG_COLOR)
		self.screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, 16))

		pygame.display.flip()


	# --------------------------- Main loop --------------------------------
	def run(self):
		self.ball.reset(direction=1)
		while self.running:
			dt = self.clock.tick(FPS) / 1000.0
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					self.running = False
				elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
					self.running = False

			self.update(dt)
			self.draw()

		pygame.quit()


def main():
	# Allow headless environments to still import the module without crashing
	if os.environ.get("SDL_VIDEODRIVER") == "dummy" and __name__ == "__main__":
		print("Running with SDL_VIDEODRIVER=dummy; no window will appear.")
	Game().run()


if __name__ == "__main__":
	main()


