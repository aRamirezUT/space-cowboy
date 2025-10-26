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

import os
import sys
import pygame
import importlib
from typing import Callable, List, Tuple

# Ensure `py-game/` is importable for the game modules and shared utils
ROOT = os.path.dirname(os.path.abspath(__file__))
PYGAME_DIR = os.path.join(ROOT, "py-game")
if PYGAME_DIR not in sys.path:
    sys.path.insert(0, PYGAME_DIR)

# Try to use shared font loader if available; fallback to system otherwise
try:
    fonts_mod = importlib.import_module('fonts.fonts')
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
        # End menu display and hand off to the game; restore menu after return
        self._teardown_display()
        try:
            mod = importlib.import_module('quickdraw')
            cls = getattr(mod, 'QuickdrawGame')
            cls().run()
        finally:
            self._recreate_display()

    def _run_twin_suns_duel(self) -> None:
        self._teardown_display()
        try:
            mod = importlib.import_module('twin_suns_duel')
            cls = getattr(mod, 'TwinSunsDuel')
            cls().run()
        finally:
            self._recreate_display()

    def _run_pong(self) -> None:
        self._teardown_display()
        try:
            mod = importlib.import_module('pong')
            cls = getattr(mod, 'Game')
            cls().run()
        finally:
            self._recreate_display()

    def _quit_menu(self) -> None:
        self.running = False

    # ------------------------- Display helpers ------------------------
    def _teardown_display(self) -> None:
        try:
            # Fully quit pygame so that games can re-initialize cleanly
            pygame.quit()
        except Exception:
            pass

    def _recreate_display(self) -> None:
        # Re-initialize pygame and rebuild display and fonts after a game exits
        pygame.init()
        flags = pygame.HWSURFACE | pygame.DOUBLEBUF | (pygame.FULLSCREEN if self.fullscreen else pygame.RESIZABLE)
        size = (0, 0) if self.fullscreen else self.base_size
        self.screen = pygame.display.set_mode(size, flags)
        self.scene = pygame.Surface(self.base_size)
        pygame.display.set_caption("Space Cowboy — Main Menu")
        # Recreate fonts because pygame.quit() invalidates them
        self._setup_fonts()

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
            dt = self.clock.tick(60) / 1000.0
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
                    elif event.key == pygame.K_F11:
                        self._toggle_fullscreen()
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        self.index = (self.index - 1) % len(self.entries)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.index = (self.index + 1) % len(self.entries)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        # Invoke the selected entry
                        label, action = self.entries[self.index]
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


if __name__ == "__main__":
    Menu().run()
