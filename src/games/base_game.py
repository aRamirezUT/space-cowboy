#!/usr/bin/env python3
import pygame

from src.fonts.fonts import load_fonts


class BaseGame():

    def __init__(self,
                 screen: pygame.Surface | None,
                 font_path: str = "",
                 width: int = 0,
                 height: int = 0):
        self.screen: pygame.Surface | None = screen
        self.fullscreen = False
        self.running = True
        self.width = width
        self.height = height

        # Store initial display size for fullscreen toggle
        if screen:
            self.initial_display_size = screen.get_size()
        else:
            self.initial_display_size = (960, 540)

        self.scene = pygame.Surface((self.width, self.height))

        # Load fonts
        try:
            f = load_fonts(small=24, medium=40, big=56, font_path=font_path)
            self.small_font = f.small
            self.big_font = f.big
            self.med_font = f.medium
        except Exception:
            self.small_font = pygame.font.SysFont("monospace", 24)
            self.big_font = pygame.font.SysFont("monospace", 56)
            self.med_font = pygame.font.SysFont("monospace", 40)

    def handle_menu_events(self, event: pygame.event.Event) -> None:
        """Common event handling for all games."""
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.VIDEORESIZE:
            self.resize_window()
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_q):
                self.running = False
            elif event.key == pygame.K_r:
                self.restart()
            elif event.key == pygame.K_F11:
                self.toggle_fullscreen()

    def resize_window(self) -> None:
        if not self.fullscreen and self.screen:
            self.screen = pygame.display.set_mode(
                self.screen.get_size(),
                pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)

    def toggle_fullscreen(self) -> None:
        if self.fullscreen:
            self.screen = pygame.display.set_mode(
                self.initial_display_size,
                pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)
            self.fullscreen = False
        else:
            self.screen = pygame.display.set_mode(
                (0, 0),
                pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.FULLSCREEN)
            self.fullscreen = True

    def render_centered_text(self,
                             text: str,
                             font: pygame.font.Font,
                             color: tuple,
                             y_offset: int = 0) -> None:
        """Render text centered horizontally at specified y position."""
        surf = font.render(text, True, color)
        x = self.width // 2 - surf.get_width() // 2
        y = self.height // 2 + y_offset
        self.scene.blit(surf, (x, y))

    def create_overlay(self, alpha: int = 0) -> pygame.Surface:
        """Create a semi-transparent overlay for UI elements."""
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))
        return overlay

    def render_text_with_outline(self, text: str, font: pygame.font.Font, text_color: tuple, 
                               pos: tuple[int, int], outline_px: int = 2, outline_color: tuple = (0, 0, 0), 
                               alpha: int | None = None) -> None:
        """Render text with an outline at the specified position."""
        x, y = pos
        label_main = font.render(text, True, text_color)
        label_outline = font.render(text, True, outline_color)
        
        if alpha is not None:
            try:
                label_outline.set_alpha(alpha)
                label_main.set_alpha(alpha)
            except Exception:
                pass
        
        # Draw outline in 8 directions
        offsets = [
            (-outline_px, 0), (outline_px, 0), (0, -outline_px), (0, outline_px),
            (-outline_px, -outline_px), (-outline_px, outline_px), 
            (outline_px, -outline_px), (outline_px, outline_px),
        ]
        for dx, dy in offsets:
            self.scene.blit(label_outline, (x + dx, y + dy))
        
        # Draw main text
        self.scene.blit(label_main, (x, y))

    def restart(self) -> None:
        pass

    def run(self) -> None:
        pass

    def draw(self) -> None:
        pass

    def render_background(self) -> None:
        pass
