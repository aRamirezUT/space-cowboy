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


import math
import os
import random
import pygame

from typing import Optional, Tuple
from src.games.base_game import BaseGame
from src.controls.controls import Controls
from src.sprites.player import Player

from src.configs.quickdraw import (
    BASE_WIDTH, BASE_HEIGHT, WINDOW_SCALE,
    BG_COLOR, FG_COLOR, GREEN, RED, YELLOW,
    PLAYER_HEIGHT_FRAC as PLAYER_H_FRAC,
    PLAYER_ASPECT_SCALE,
    PLAYER_MARGIN_FRAC,
    GROUND_FRAC, FOOT_MARGIN_PX,
    TEXT_OUTLINE_PX, TEXT_OUTLINE_COLOR,
    LEFT_HOLSTERED, RIGHT_HOLSTERED, LEFT_DRAWN,
    RIGHT_DRAWN, FONT_PATH,
    DIMMED_ALPHA, WINNER_ANIMATION_DURATION, 
    BULLET_DURATION, KILL_DURATION, COUNTDOWN_TOTAL,
)

# Logical world size (fixed) and initial display size
WIDTH, HEIGHT = BASE_WIDTH, BASE_HEIGHT
INITIAL_DISPLAY_SIZE = (int(BASE_WIDTH * WINDOW_SCALE), int(BASE_HEIGHT * WINDOW_SCALE))

# Player sizing and placement derived from config
PLAYER_W = int(HEIGHT * PLAYER_H_FRAC * PLAYER_ASPECT_SCALE)
PLAYER_H = int(HEIGHT * PLAYER_H_FRAC)
MARGIN_X = int(WIDTH * PLAYER_MARGIN_FRAC)


class QuickdrawGame(BaseGame):
    def __init__(
        self, 
        controls: Controls, 
        screen: Optional[pygame.Surface] = None, 
    ) -> None:
        super().__init__(screen, font_path=FONT_PATH, width=WIDTH, height=HEIGHT)
        
        pygame.display.set_caption("MYO BEBOP Quickdraw")
        self.clock = pygame.time.Clock()
        self.controls = controls

        # Place cowboys near the ground line defined by config
        ground_y = int(HEIGHT * GROUND_FRAC)
        base_y = ground_y - FOOT_MARGIN_PX - PLAYER_H
        self.left = Player(MARGIN_X, base_y, PLAYER_W, PLAYER_H, HEIGHT, image_name=LEFT_HOLSTERED)
        self.right = Player(WIDTH - MARGIN_X - PLAYER_W, base_y, PLAYER_W, PLAYER_H, HEIGHT, image_name=RIGHT_HOLSTERED)

        # Initialize game state by calling restart
        self.countdown_total = COUNTDOWN_TOTAL
        self.win_anim_duration = WINNER_ANIMATION_DURATION
        self.bullet_duration = BULLET_DURATION
        self.kill_duration = KILL_DURATION
        self.restart()

    # --------------------------- Helper Methods ---------------------------

    def _handle_phase_transitions(self) -> None:
        """Handle the ready->set->delay->draw phase transitions."""
        elapsed = self.current_time - self.phase_start_ms
        if self.phase == "ready" and elapsed >= 1000:
            self.phase = "set"
            self.phase_start_ms = self.current_time
        elif self.phase == "set" and elapsed >= 1000:
            self.phase = "delay"
            self.phase_start_ms = self.current_time
        elif self.phase == "delay" and self.random_delay_ms is not None and elapsed >= self.random_delay_ms:
            # Start DRAW phase
            self.phase = "draw"
            self.draw_enabled = True
            self.draw_signal_ms = self.current_time

    def _handle_bullet_animation(self) -> None:
        """Handle bullet animation and trigger kill effect when complete."""
        if self.bullet_active and self.bullet_start_ms:
            t = (self.current_time - self.bullet_start_ms) / float(self.bullet_duration)
            if t >= 1.0:
                self.bullet_active = False
                # Trigger kill effect on loser
                self.kill_target = self.bullet_to
                self.kill_start_ms = self.current_time

    def run(self):
        while self.running:
            self.current_time = pygame.time.get_ticks()
            for event in pygame.event.get():
                self.handle_menu_events(event)
            # Poll merged input each frame for 0->1 edges
            self._handle_draw_inputs()
            self._update()
            self._render()

    def handle_menu_events(self, event) -> None:
        super().handle_menu_events(event)
        # Handle game-specific events
        if event.type == pygame.KEYDOWN:
            if self.waiting_for_start and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self._arm_countdown()

    def _arm_countdown(self):
        self.waiting_for_start = False
        self.phase = "ready"
        self.phase_start_ms = self.current_time

    def restart(self):
        self.waiting_for_start = True
        self.winner = None
        self.foul_by = None
        self.draw_signal_ms: int = 0
        self.draw_enabled: bool = False
        self.phase: str = ""
        self.phase_start_ms: int = 0
        self.random_delay_ms: int = random.randint(500, 2000)
        self.prev_inputs: Tuple[float, float] = (0.0, 0.0)
        # Clear bullet/kill state
        self.bullet_active: bool = False
        self.bullet_from: int = 0
        self.bullet_to: int = 0
        self.bullet_start: Tuple[float, float] = (0.0, 0.0)
        self.bullet_end: Tuple[float, float] = (0.0, 0.0)
        self.bullet_start_ms: int = 0
        self.kill_start_ms: int = 0
        self.kill_target: int = 0
        
        # Reset sprites to holstered state
        self._set_player_pose(0, drawn=False)
        self._set_player_pose(1, drawn=False)
        # recenters to ground-based placement
        ground_y = int(HEIGHT * GROUND_FRAC)
        base_y = ground_y - FOOT_MARGIN_PX - PLAYER_H
        self.left.y = base_y
        self.right.y = base_y
        self.render_background()

    def _handle_draw_inputs(self):
        """Detect 0->1 edges from merged keyboard/BLE binary input.
        Before DRAW: edge is a foul; after DRAW: edge is a valid draw.
        """
        if self.winner is not None:
            return
        keys = pygame.key.get_pressed()
        p1_new, p2_new = self.controls.get_inputs(keys, threshold=0.5)

        p1_prev, p2_prev = self.prev_inputs
        # Edge triggers
        if p1_new >= 0.5 and p1_prev <= 0.5:
            if not self.waiting_for_start and not self.draw_enabled:
                self._declare_foul(0)
            elif self.draw_enabled:
                self._declare_winner(0)
        elif p2_new >= 0.5 and p2_prev <= 0.5:
            if not self.waiting_for_start and not self.draw_enabled:
                self._declare_foul(1)
            elif self.draw_enabled:
                self._declare_winner(1)
        self.prev_inputs = (p1_new, p2_new)

    def _declare_winner(self, who: int):
        self.winner = who
        self.win_anim_start_ms = self.current_time
        # Winner switches to drawn pose
        self._set_player_pose(who, drawn=True)
        self._spawn_bullet(from_player=who, to_player=1 - who)

    def _declare_foul(self, who: int):
        # A player drew before DRAW: they lose, the other wins.
        if self.winner:
            return
        self.foul_by = who
        self._declare_winner(1 - who)

    def _update(self):
        if self.waiting_for_start:
            return
        # Handle phase transitions and bullet animations
        self._handle_phase_transitions()
        self._handle_bullet_animation()

    def _render(self):
        self.scene.blit(self._bg_prepared, (0, 0))
        # Draw players (with winner animation). Images are already correctly oriented,
        # so we pass facing_right=True to avoid flipping.
        self._draw_player(self.left, facing_right=True, is_winner=(self.winner == 0), is_kill_target=(self.kill_target == 0))
        self._draw_player(self.right, facing_right=True, is_winner=(self.winner == 1), is_kill_target=(self.kill_target == 1))

        # Bullet (on top of players)
        if self.bullet_active and self.bullet_start_ms:
            t = max(0.0, min(1.0, (self.current_time - self.bullet_start_ms) / float(self.bullet_duration)))
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
            title_surf = self.big_font.render("Quickdraw Duel", True, FG_COLOR)
            title_x = WIDTH // 2 - title_surf.get_width() // 2
            self.render_text_with_outline("Quickdraw Duel", self.big_font, FG_COLOR, (title_x, HEIGHT//2 - 80))
            
            subtitle_surf = self.small_font.render("Press SPACE or ENTER to arm", True, FG_COLOR)
            subtitle_x = WIDTH // 2 - subtitle_surf.get_width() // 2
            self.render_text_with_outline("Press SPACE or ENTER to arm", self.small_font, FG_COLOR, (subtitle_x, HEIGHT//2 + 8))
        else:
            if self.winner is None:
                # Show phase text: READY -> Set -> (silent random delay) -> DRAW! with distinct colors and background
                if self.phase == "ready":
                    ready_surf = self.med_font.render("READY", True, RED)
                    ready_x = WIDTH // 2 - ready_surf.get_width() // 2
                    self.render_text_with_outline("READY", self.med_font, RED, (ready_x, HEIGHT//2 - 60))
                elif self.phase == "set":
                    set_surf = self.med_font.render("Set", True, YELLOW)
                    set_x = WIDTH // 2 - set_surf.get_width() // 2
                    self.render_text_with_outline("Set", self.med_font, YELLOW, (set_x, HEIGHT//2 - 60))
                elif self.phase == "draw":
                    if self.draw_signal_ms and (self.current_time - self.draw_signal_ms) < 900:
                        draw_surf = self.med_font.render("DRAW!", True, GREEN)
                        draw_x = WIDTH // 2 - draw_surf.get_width() // 2
                        self.render_text_with_outline("DRAW!", self.med_font, GREEN, (draw_x, HEIGHT//2 - 60))

        if self.winner is not None:
            if self.foul_by is not None:
                # Show foul message prominently
                player = "Player 1" if self.foul_by == 0 else "Player 2"
                foul_text = f"Too soon, {player} you lose!"
                foul_surf = self.med_font.render(foul_text, True, (240, 120, 120))
                foul_x = WIDTH // 2 - foul_surf.get_width() // 2
                self.render_text_with_outline(foul_text, self.med_font, (240, 120, 120), (foul_x, HEIGHT//2 - 160))
                msg = "Player 1 wins!" if self.winner == 0 else "Player 2 wins!"
            else:
                msg = "Player 1 drew first!" if self.winner == 0 else "Player 2 drew first!"
            
            msg_surf = self.med_font.render(msg, True, (240, 210, 80))
            msg_x = WIDTH // 2 - msg_surf.get_width() // 2
            self.render_text_with_outline(msg, self.med_font, (240, 210, 80), (msg_x, HEIGHT//2 - 120))
            
            restart_surf = self.small_font.render("Press R to restart • Q to quit", True, FG_COLOR)
            restart_x = WIDTH // 2 - restart_surf.get_width() // 2
            self.render_text_with_outline("Press R to restart • Q to quit", self.small_font, FG_COLOR, (restart_x, HEIGHT//2 - 76))        # Scale scene to display
        if self.screen is not None:
            display_size = self.screen.get_size()
            scaled = pygame.transform.smoothscale(self.scene, display_size)
            self.screen.blit(scaled, (0, 0))
            pygame.display.flip()

    def _draw_nameplate(self, player: Player, text: str, *, dimmed: bool = False):
        # Render outlined title below the player's sprite (no background box)
        # Place under the sprite, clamp to bottom margin
        # Compute text width first using font metrics
        label_tmp = self.small_font.render(text, True, FG_COLOR)
        tx = int(player.x + player.w // 2 - label_tmp.get_width() // 2)
        ty = int(min(HEIGHT - label_tmp.get_height() - 4, player.y + player.h + 6))
        alpha = 255 if not dimmed else DIMMED_ALPHA
        self.render_text_with_outline(text, self.small_font, FG_COLOR, (tx, ty), 
                                     outline_px=TEXT_OUTLINE_PX, outline_color=TEXT_OUTLINE_COLOR, alpha=alpha)
        
    def _draw_player(self, player: Player, facing_right: bool, is_winner: bool, is_kill_target: bool = False):
        # Kill effect overrides normal drawing for the losing player once triggered
        if is_kill_target and self.kill_start_ms:
            prog = max(0.0, min(1.0, (self.current_time - self.kill_start_ms) / float(self.kill_duration)))
            # Visual: fade out, slight rotate and drop
            angle = -12.0 * prog  # small tilt
            drop = player.h * 0.18 * prog
            alpha = int(255 * (1.0 - prog))
            base = player.get_image(facing_right)
            base.set_alpha(alpha)
            rotated = pygame.transform.rotozoom(base, angle, 1.0)
            rw, rh = rotated.get_width(), rotated.get_height()
            off_x = player.x + (player.w - rw) // 2
            off_y = player.y + (player.h - rh) // 2 + int(drop)
            self.scene.blit(rotated, (int(off_x), int(off_y)))
            return
        # If animating winner, apply a simple pulsing scale effect to the sprite image
        if is_winner:
            pulse_time = (self.current_time - pygame.time.get_ticks()) / 1000.0
            # Damped pulse: amplitude decays over ~1.4s
            amp = max(0.0, 0.16 * math.exp(-1.6 * pulse_time))
            pulse = math.sin(2.0 * math.pi * (2.2 * pulse_time))  # 2.2 Hz pulse
            scale = 1.0 + amp * pulse
            # Access cached image from Player and scale it
            img = player.get_image(facing_right)
            if img is not None:
                iw, ih = img.get_width(), img.get_height()
                new_w = max(1, int(round(iw * scale)))
                new_h = max(1, int(round(ih * scale)))
                scaled = pygame.transform.smoothscale(img, (new_w, new_h))
                # Center the scaled image within the player's bounding box
                off_x = player.x + (player.w - new_w) // 2
                off_y = player.y + (player.h - new_h) // 2
                self.scene.blit(scaled, (int(off_x), int(off_y)))
                return
            # Fallback to normal draw if anything goes wrong
        player.draw(self.scene, facing_right=facing_right)

    def render_background(self):
        """Load and crop the western background to cover the world size.

        Uses a "cover" fit: maintains aspect ratio, scales up so the image fully
        covers (WIDTH x HEIGHT), then center-crops to exactly that size.
        Falls back to the starfield if the image isn't available.
        """
        try:
            bg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sprites", "images", "western-background.png")
            src = pygame.image.load(bg_path).convert()
        except Exception as e:
            raise RuntimeError(f"Error loading background image: {e}")
        try:
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
        except Exception as e:
            raise RuntimeError(f"Error processing background image: {e}")

    def _set_player_pose(self, who: int, drawn: bool):
        """Swap the player's sprite between holstered/drawn poses.
        Images are pre-oriented (east for left, west for right), so we avoid flips by
        always drawing with facing_right=True.
        """
        player = self.left if who == 0 else self.right
        if who == 0:
            image_name = LEFT_DRAWN if drawn else LEFT_HOLSTERED
        else:
            image_name = RIGHT_DRAWN if drawn else RIGHT_HOLSTERED
        player.change_sprite(image_name)

    def _spawn_bullet(self, from_player: int, to_player: int):
        # Determine start and end coordinates based on player bounds
        shooter = self.left if from_player == 0 else self.right
        target = self.left if to_player == 0 else self.right
        # Approximate muzzle position as slightly forward from player center
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
