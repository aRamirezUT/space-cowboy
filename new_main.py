#!/usr/bin/env python3
"""
Space Cowboy: Main Menu

Use this menu to launch the available pygame experiences:
- Quickdraw Duel
- Twin Suns Duel
- Pong

Controls
- Up/Down: navigate
- Enter/Return: select
- F11: toggle fullscreen
- Q or ESC: quit

This script must be run from the repository root.
"""
from __future__ import annotations
from typing import Callable, List, Tuple

import os
import pygame
import importlib

from src.controls.controls import Controls

ROOT = os.path.dirname(os.path.abspath(__file__))

# Try to use shared font loader if available; fallback to system otherwise
try:
    fonts_mod = importlib.import_module('src.fonts.fonts')
    load_fonts = getattr(fonts_mod, 'load_fonts', None)
except Exception:
    load_fonts = None  # type: ignore


class Menu:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Space Cowboy — Main Menu")
        # Windowed default; F11 toggles fullscreen
        self.fullscreen = False
        self.base_size = (960, 540)
        self.screen = pygame.display.set_mode(self.base_size, pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)
        self.scene = pygame.Surface(self.base_size)
        self.clock = pygame.time.Clock()

        # Fonts
        self.font_small = None
        self.font_big = None
        self._setup_fonts()
        
        # Create controller
        self.controls = Controls()
        

        # Menu entries: label and callable to run
        self.entries: List[Tuple[str, Callable[[], None]]] = [
            ("Quickdraw Duel", self._run_quickdraw),
            ("Twin Suns Duel", self._run_twin_suns_duel),
            ("Pong", self._run_pong),
            ("Quit", self._quit_menu),
        ]
        self.index = 0
        self.running = True

    # ------------------------- Game Launchers -------------------------
    def _run_quickdraw(self) -> None:
        # Launch game in hosted mode using the existing window for seamless return
        mod = importlib.import_module('src.quickdraw')
        cls = getattr(mod, 'QuickdrawGame')
        cls(controls=self.controls, screen=self.screen, own_display=False).run()

    def _run_twin_suns_duel(self) -> None:
        mod = importlib.import_module('src.twin_suns_duel')
        cls = getattr(mod, 'TwinSunsDuel')
        cls(controls=self.controls, screen=self.screen, own_display=False).run()

    def _run_pong(self) -> None:
        mod = importlib.import_module('src.pong')
        cls = getattr(mod, 'Game')
        cls(controls=self.controls, screen=self.screen, own_display=False).run()

    def _quit_menu(self) -> None:
        self.running = False

    # ------------------------- Display helpers ------------------------
    def _teardown_display(self) -> None:
        # No-op in seamless mode; we keep the window and pygame initialized
        return

    def _recreate_display(self) -> None:
        # No-op: we never tore down, keep current window. Ensure scene matches base size.
        if self.screen is None:
            flags = pygame.HWSURFACE | pygame.DOUBLEBUF | (pygame.FULLSCREEN if self.fullscreen else pygame.RESIZABLE)
            size = (0, 0) if self.fullscreen else self.base_size
            self.screen = pygame.display.set_mode(size, flags)
        self.scene = pygame.Surface(self.base_size)
        pygame.display.set_caption("Space Cowboy — Main Menu")

    def _setup_fonts(self) -> None:
        try:
            pygame.font.init()
        except Exception:
            pass
        # Default system fonts
        small = pygame.font.SysFont("monospace", 22)
        big = pygame.font.SysFont("monospace", 48)
        # Try shared game fonts if available
        if load_fonts:
            try:
                f = load_fonts(small=22, medium=32, big=56, font_path=None)
                small = f.small
                big = f.big
            except Exception:
                pass
        self.font_small = small
        self.font_big = big

    # ----------------------------- Loop -------------------------------
    def run(self) -> None:
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    if not self.fullscreen:
                        # Keep resizable window; draw is scaled anyway
                        pygame.display.set_mode(event.size, pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        self.running = False
                    elif event.key == pygame.K_c:
                        # Guided calibration with progress bars (RELAX -> wait 1s -> FLEX)
                        self._run_calibration_with_progress()
                    elif event.key == pygame.K_F11:
                        self._toggle_fullscreen()
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        self.index = (self.index - 1) % len(self.entries)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.index = (self.index + 1) % len(self.entries)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        # Invoke the selected entry
                        _, action = self.entries[self.index]
                        action()

            self._draw()

        pygame.quit()

    def _toggle_fullscreen(self) -> None:
        if self.fullscreen:
            self.fullscreen = False
            self.screen = pygame.display.set_mode(self.base_size, pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)
        else:
            self.fullscreen = True
            self.screen = pygame.display.set_mode((0, 0), pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.FULLSCREEN)

    def _draw(self) -> None:
        # Background
        self.scene.fill((12, 12, 16))
        # Title
        title = self.font_big.render("Space Cowboy", True, (235, 235, 245))
        tx = self.scene.get_width() // 2 - title.get_width() // 2
        self.scene.blit(title, (tx, 40))

        # Entries
        base_y = 160
        line_h = 44
        for i, (label, _) in enumerate(self.entries):
            selected = (i == self.index)
            color = (80, 200, 120) if selected else (235, 235, 245)
            text = self.font_small.render(("→ " if selected else "  ") + label, True, color)
            x = self.scene.get_width() // 2 - text.get_width() // 2
            y = base_y + i * line_h
            self.scene.blit(text, (x, y))

        # Footer
        footer = self.font_small.render("Up/Down: Navigate  •  Enter: Select  •  F11: Fullscreen  •  Q/Esc: Quit", True, (180, 180, 190))
        fx = self.scene.get_width() // 2 - footer.get_width() // 2
        fy = self.scene.get_height() - 36
        self.scene.blit(footer, (fx, fy))

        # Present scaled
        display_size = self.screen.get_size()
        scaled = pygame.transform.smoothscale(self.scene, display_size)
        self.screen.blit(scaled, (0, 0))
        pygame.display.flip()

    def _show_calibration_summary(self, p1_relax, p1_flex, p2_relax, p2_flex) -> None:
        # Render a live overlay with calibration values and input booleans (0/1) per player.
        # Exit only on quit keywords: Q or ESC.
        clock = pygame.time.Clock()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
                    return

            # Poll current input as binary booleans (thresholded)
            try:
                v1, v2 = self.controls.get_data()
            except Exception:
                v1, v2 = 0.0, 0.0
            b1 = 1 if v1 > 0.5 else 0
            b2 = 1 if v2 > 0.5 else 0

            # Draw overlay to scene
            self.scene.fill((12, 12, 16))
            title = self.font_big.render("Calibration complete", True, (80, 200, 120))
            self.scene.blit(title, (self.scene.get_width()//2 - title.get_width()//2, 60))

            # Values
            def fmt(v):
                try:
                    return f"{float(v):.1f}"
                except Exception:
                    return "-"
            lines = [
                f"Player 1: Relax {fmt(p1_relax)}  |  Flex {fmt(p1_flex)}",
                f"Player 2: Relax {fmt(p2_relax)}  |  Flex {fmt(p2_flex)}",
                f"Input P1: {b1}  |  Input P2: {b2}",
                "Press Q or Esc to return",
            ]
            y = 160
            for i, text in enumerate(lines):
                # Dim the instruction line slightly
                color = (235, 235, 245) if i < 3 else (180, 180, 190)
                surf = self.font_small.render(text, True, color)
                self.scene.blit(surf, (self.scene.get_width()//2 - surf.get_width()//2, y))
                y += 42

            # Present scaled
            display_size = self.screen.get_size()
            scaled = pygame.transform.smoothscale(self.scene, display_size)
            self.screen.blit(scaled, (0, 0))
            pygame.display.flip()
            clock.tick(30)

    def _run_calibration_with_progress(self) -> None:
        """Show a 5s RELAX progress, wait 1s, then 5s FLEX progress, calling controls calibrations.
        Does not modify controls.* functions; only orchestrates timing/UI.
        """
        # Phase 1: RELAX progress bar (5 seconds)
        self._show_phase_progress("RELAX", seconds=5)
        # Perform RELAX calibration (records last 3 seconds internally)
        try:
            self.controls.calibrate_relax()
        except Exception as e:
            # Show brief error overlay and return
            self._show_error_overlay(f"Calibration failed (RELAX): {e}")
            return

        # Inter-phase wait: 1 second (UI responsive)
        self._wait_seconds(1.0)

        # Phase 2: FLEX progress bar (5 seconds)
        self._show_phase_progress("FLEX", seconds=5)
        # Perform FLEX calibration
        try:
            self.controls.calibrate_flex()
        except Exception as e:
            self._show_error_overlay(f"Calibration failed (FLEX): {e}")
            return

        # Summary overlay
        p1r = getattr(self.controls, 'P1_RELAX', None)
        p1f = getattr(self.controls, 'P1_FLEX', None)
        p2r = getattr(self.controls, 'P2_RELAX', None)
        p2f = getattr(self.controls, 'P2_FLEX', None)
        self._show_calibration_summary(p1r, p1f, p2r, p2f)

    def _show_phase_progress(self, label: str, *, seconds: int) -> None:
        """Render a centered title and a progress bar counting up to `seconds`. ESC cancels."""
        clock = pygame.time.Clock()
        start = pygame.time.get_ticks()
        duration_ms = max(1, int(seconds * 1000))
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
                    return

            now = pygame.time.get_ticks()
            elapsed = now - start
            frac = max(0.0, min(1.0, elapsed / duration_ms))

            # Draw
            self.scene.fill((12, 12, 16))
            title = self.font_big.render(label, True, (240, 210, 80))
            self.scene.blit(title, (self.scene.get_width()//2 - title.get_width()//2, 80))

            bar_w = int(self.scene.get_width() * 0.56)
            bar_h = 24
            bx = self.scene.get_width()//2 - bar_w//2
            by = self.scene.get_height()//2 - bar_h//2
            pygame.draw.rect(self.scene, (30, 30, 36), (bx, by, bar_w, bar_h), border_radius=8)
            fill_w = int(round(bar_w * frac))
            if fill_w > 0:
                pygame.draw.rect(self.scene, (80, 200, 120), (bx, by, fill_w, bar_h), border_radius=8)
            pygame.draw.rect(self.scene, (60, 60, 70), (bx, by, bar_w, bar_h), width=2, border_radius=8)

            # Hint
            hint = self.font_small.render("Hold steady…", True, (180, 180, 190))
            self.scene.blit(hint, (self.scene.get_width()//2 - hint.get_width()//2, by + bar_h + 18))

            # Present scaled
            display_size = self.screen.get_size()
            scaled = pygame.transform.smoothscale(self.scene, display_size)
            self.screen.blit(scaled, (0, 0))
            pygame.display.flip()

            if elapsed >= duration_ms:
                return
            clock.tick(60)

    def _wait_seconds(self, seconds: float) -> None:
        clock = pygame.time.Clock()
        start = pygame.time.get_ticks()
        duration_ms = int(seconds * 1000)
        while pygame.time.get_ticks() - start < duration_ms:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
            # Draw a subtle dim overlay between phases
            self.scene.fill((12, 12, 16))
            txt = self.font_small.render("Get ready…", True, (180, 180, 190))
            self.scene.blit(txt, (self.scene.get_width()//2 - txt.get_width()//2, self.scene.get_height()//2 - txt.get_height()//2))
            display_size = self.screen.get_size()
            scaled = pygame.transform.smoothscale(self.scene, display_size)
            self.screen.blit(scaled, (0, 0))
            pygame.display.flip()
            clock.tick(60)

    def _show_error_overlay(self, message: str) -> None:
        clock = pygame.time.Clock()
        start = pygame.time.get_ticks()
        while pygame.time.get_ticks() - start < 2000:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
            self.scene.fill((20, 12, 12))
            title = self.font_big.render("Calibration error", True, (220, 120, 120))
            msg = self.font_small.render(message, True, (235, 235, 245))
            self.scene.blit(title, (self.scene.get_width()//2 - title.get_width()//2, 80))
            self.scene.blit(msg, (self.scene.get_width()//2 - msg.get_width()//2, 140))
            display_size = self.screen.get_size()
            scaled = pygame.transform.smoothscale(self.scene, display_size)
            self.screen.blit(scaled, (0, 0))
            pygame.display.flip()
            clock.tick(60)

    # ---------------------- EXG client plumbing ----------------------
    def _make_exg_client(self):
        """Instantiate a shared EXG client if available; otherwise return None for keyboard-only play."""
        try:
            from src.controls.exg.exg_client import EXGClient
            return EXGClient()
        except RuntimeError as e:
            # Gracefully fallback to keyboard controls if no stream is available
            print(f"[Space Cowboy] EXG input disabled: {e}")
            return None


if __name__ == "__main__":
    Menu().run()
