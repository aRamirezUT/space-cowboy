"""Base game functionality shared across all games."""

import os
import pygame

from typing import Optional
from src.fonts.fonts import FontManager
from src.games.config import FONT_PATH, SPRITES_DIR, SPRITE_PATHS
from src.controls.controls import Controls




class FontMixin:
    """Mixin class to provide standardized font loading for all games."""
    
    def setup_fonts(self) -> None:
        """Setup fonts using the centralized font manager."""
        font_manager = FontManager.initialize(FONT_PATH)
        
        # Provide standard font attributes that all games can use
        self.small_font = font_manager.small
        self.med_font = font_manager.medium  
        self.big_font = font_manager.big
        
        # Add some common aliases that games might use
        self.font = font_manager.small  # Default font
        self.font_small = font_manager.small
        self.font_medium = font_manager.medium
        self.font_big = font_manager.big
        
        # Store the font manager for direct access if needed
        self._font_manager = font_manager



    @staticmethod
    def get_sprite_path(sprite_name: str, game_type: str = "common") -> str:
        """Get the absolute path to a sprite file.
        
        Args:
            sprite_name: Name of the sprite file or key in SPRITE_PATHS
            game_type: Type of game ("quickdraw", "twin_suns", "common")
            
        Returns:
            Absolute path to the sprite file
        """
        # Get the project root (space-cowboy directory)
        current_dir = os.path.dirname(os.path.abspath(__file__))  # src/games/
        src_dir = os.path.dirname(current_dir)  # src/
        project_root = os.path.dirname(src_dir)  # space-cowboy/
        
        sprites_dir = os.path.join(project_root, SPRITES_DIR)
        
        # Check if sprite_name is a key in SPRITE_PATHS
        if game_type in SPRITE_PATHS and sprite_name in SPRITE_PATHS[game_type]:
            filename = SPRITE_PATHS[game_type][sprite_name]
        else:
            # Treat sprite_name as the actual filename
            filename = sprite_name
        
        return os.path.join(sprites_dir, filename)


class DisplayMixin:
    """Mixin class to provide shared display and input functionality."""
    
    def __init__(self, *, controls: Controls, screen: Optional[pygame.Surface] = None, 
                 base_size: tuple = (960, 540)):
        """Initialize display functionality.
        
        Args:
            controls: Controls instance for input handling
            screen: Optional existing pygame surface to use
            base_size: Base resolution for the game scene
        """
        self.controls = controls
        self.screen = screen
        self.base_size = base_size
        self.scene = pygame.Surface(base_size)
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Determine fullscreen state from current display if available
        if pygame.display.get_surface() is not None:
            current_size = pygame.display.get_window_size()
            surface_size = pygame.display.get_surface().get_size()
            self.fullscreen = current_size == surface_size
        else:
            self.fullscreen = False
    
    def toggle_fullscreen(self) -> None:
        """Toggle between fullscreen and windowed mode."""
        if self.fullscreen:
            self.fullscreen = False
            self.screen = pygame.display.set_mode(
                self.base_size, 
                pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE
            )
        else:
            self.fullscreen = True
            self.screen = pygame.display.set_mode(
                (0, 0), 
                pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.FULLSCREEN
            )
    
    def resize_window(self) -> None:
        """Handle window resize events."""
        if not self.fullscreen and self.screen is not None:
            pygame.display.set_mode(
                self.screen.get_size(), 
                pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE
            )
    
    def handle_common_events(self, event: pygame.event.Event) -> bool:
        """Handle common input events shared across games.
        
        Args:
            event: pygame event to handle
            
        Returns:
            True if the event was handled, False otherwise
        """
        if event.type == pygame.QUIT:
            self.running = False
            return True
        elif event.type == pygame.VIDEORESIZE:
            self.resize_window()
            return True
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_q):
                self.running = False
                return True
            elif event.key == pygame.K_F11:
                self.toggle_fullscreen()
                return True
        
        return False
    
    def present_scene(self) -> None:
        """Present the scene surface to the screen with proper scaling."""
        if self.screen is not None:
            display_size = self.screen.get_size()
            scaled = pygame.transform.smoothscale(self.scene, display_size)
            self.screen.blit(scaled, (0, 0))
            pygame.display.flip()


class BaseGame(FontMixin, DisplayMixin):
    """Base class for games that provides common functionality."""
    
    def __init__(self, *, controls: Controls, screen: Optional[pygame.Surface] = None, 
                 base_size: tuple = (960, 540)):
        # Initialize mixins
        FontMixin.__init__(self)
        DisplayMixin.__init__(self, controls=controls, screen=screen, base_size=base_size)
        
        # Setup fonts after mixin initialization
        self.setup_fonts()

    @property
    def fonts(self):
        """Access to the font manager's fonts."""
        return self._font_manager.fonts

    @staticmethod
    def get_sprite_path(sprite_name: str, game_type: str = "common") -> str:
        """Get the absolute path to a sprite file.
        
        Args:
            sprite_name: Name of the sprite file or key in SPRITE_PATHS
            game_type: Type of game ("quickdraw", "twin_suns", "common")
            
        Returns:
            Absolute path to the sprite file
        """
        # Get the project root (space-cowboy directory)
        current_dir = os.path.dirname(os.path.abspath(__file__))  # src/games/
        src_dir = os.path.dirname(current_dir)  # src/
        project_root = os.path.dirname(src_dir)  # space-cowboy/
        
        sprites_dir = os.path.join(project_root, SPRITES_DIR)
        
        # Check if sprite_name is a key in SPRITE_PATHS
        if game_type in SPRITE_PATHS and sprite_name in SPRITE_PATHS[game_type]:
            filename = SPRITE_PATHS[game_type][sprite_name]
        else:
            # Treat sprite_name as the actual filename
            filename = sprite_name
        
        return os.path.join(sprites_dir, filename)