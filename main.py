#!/usr/bin/env python3
import pygame

from typing import Callable, List, Tuple
from src.sprites.background import render_starfield_surface
from src.controls.controls import Controls
from src.fonts.fonts import load_fonts
from src.games.quickdraw import QuickdrawGame
from src.games.twin_suns_duel import TwinSunsDuel
from src.games.pong import Pong
from src.games.calibration import Calibration
from src.games.base_game import FontMixin, DisplayMixin
from src.games.config import (
    FONT_PATH, BASE_WIDTH, BASE_HEIGHT,
    STAR_DENSITY,
    STAR_SIZE_MIN,
    STAR_SIZE_MAX
)

class Menu(FontMixin, DisplayMixin):
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("MYO BEBOP: Space Cowboy — Main Menu")
        
        # Initialize controls first
        controls = Controls()
        
        # Initialize the display with our base size
        base_size = (960, 540)
        screen = pygame.display.set_mode(base_size, pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)
        
        # Initialize mixins
        FontMixin.__init__(self)
        DisplayMixin.__init__(self, controls=controls, screen=screen, base_size=base_size)
        
        # Setup fonts after mixin initialization
        self.setup_fonts()
        
        self.index = 0
        self._bg_prepared = render_starfield_surface(
                BASE_WIDTH,
                BASE_HEIGHT,
                density=STAR_DENSITY,
                size_min=STAR_SIZE_MIN,
                size_max=STAR_SIZE_MAX,
                bg_color=(12, 12, 16),
            )
        self.menu: List[Tuple[str, Callable[[], None]]] = [
            ("Quickdraw Duel", self.run_quickdraw),
            ("Twin Suns Duel", self.run_twin_suns_duel),
            ("Pong", self.run_pong),
            ("Calibration", self.run_calibration)
        ]

    # Game Launchers
    def run_quickdraw(self) -> None:
        QuickdrawGame(controls=self.controls, screen=self.screen).run()

    def run_twin_suns_duel(self) -> None:
        TwinSunsDuel(controls=self.controls, screen=self.screen).run()

    def run_pong(self) -> None:
        Pong(controls=self.controls, screen=self.screen).run()

    def run_calibration(self) -> None:
        Calibration(controls=self.controls, screen=self.screen).run()
        
    # Entry point
    # Unfortunately match/case is not supported for pygame.event.get()
    # Bear with the block indentation.
    def run(self) -> None:
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.resize_window()
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        self.running = False
                    elif event.key == pygame.K_F11:
                        self.toggle_fullscreen()
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        self.move_selection_up()
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.move_selection_down()
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.invoke_action()
            if self.running:
                self.draw()
        pygame.quit()

    # Menu actions
    def invoke_action(self) -> None:
        _, action = self.menu[self.index]
        action()

    def move_selection_up(self) -> None:
        self.index = (self.index - 1) % len(self.menu)

    def move_selection_down(self) -> None:
        self.index = (self.index + 1) % len(self.menu)

    def resize_window(self) -> None:
        if not self.fullscreen:
            pygame.display.set_mode(self.screen.get_size(), pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)

    def toggle_fullscreen(self) -> None:
        if self.fullscreen:
            self.fullscreen = False
            self.screen = pygame.display.set_mode(self.base_size, pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)
        else:
            self.fullscreen = True
            self.screen = pygame.display.set_mode((0, 0), pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.FULLSCREEN)

    def draw(self) -> None:
        # Background
        if self._bg_prepared is not None:
            self.scene.blit(self._bg_prepared, (0, 0))
        else:
            self.scene.fill((12, 12, 16))
        # Title
        title = self.big_font.render("MYO BEBOP", True, (235, 235, 245))
        tx = self.scene.get_width() // 2 - title.get_width() // 2
        self.scene.blit(title, (tx, 40))

        # Entries
        base_y = 160
        line_h = 44
        for i, (label, _) in enumerate(self.menu):
            selected = (i == self.index)
            color = (80, 200, 120) if selected else (235, 235, 245)
            text = self.small_font.render(("→ " if selected else "  ") + label, True, color)
            x = self.scene.get_width() // 2 - text.get_width() // 2
            y = base_y + i * line_h
            self.scene.blit(text, (x, y))

        # Create Footer
        footer = self.small_font.render("Up/Down: Navigate  •  Enter: Select  •  F11: Fullscreen  •  Q/Esc: Quit", True, (180, 180, 190))
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
