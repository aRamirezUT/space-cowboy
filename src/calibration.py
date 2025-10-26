from __future__ import annotations

import time
from typing import Tuple

import pygame

try:
    from .controls import Controls
except ImportError:  # pragma: no cover - direct script execution fallback
    from controls import Controls  # type: ignore

# Load shared font loader and configured font path
try:
    from .fonts.fonts import load_fonts
except Exception:  # pragma: no cover
    load_fonts = None  # type: ignore
try:
    from config import FONT_PATH  # repo-level config
except Exception:  # pragma: no cover
    FONT_PATH = None  # type: ignore


class Calibration:
    """Simple EMG calibration flow + binary input monitor."""

    def __init__(
        self,
        *,
        controls: Controls,
        screen: pygame.Surface | None = None,
        own_display: bool | None = None,
        stage_seconds: float = 5.0,
    ) -> None:
        pygame.init()
        pygame.font.init()

        self.controls = controls
        self.stage_seconds = stage_seconds
        self._owns_display = bool(own_display) if own_display is not None else (screen is None)
        self.base_size = (960, 540)
        if self._owns_display:
            pygame.display.set_caption("MYO BEBOP — Calibration")
            self.screen = pygame.display.set_mode(self.base_size, pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)
        else:
            self.screen = screen  # type: ignore[assignment]
            try:
                pygame.display.set_caption("MYO BEBOP — Calibration")
            except Exception:
                pass

        self.scene = pygame.Surface(self.base_size)
        self.clock = pygame.time.Clock()
        # Prefer shared custom font; fallback to system monospace
        if load_fonts is not None:
            try:
                f = load_fonts(small=24, medium=32, big=64, font_path=FONT_PATH)
                self.small_font = f.small
                self.med_font = f.medium
                self.big_font = f.big
            except Exception:
                self.big_font = pygame.font.SysFont("monospace", 64)
                self.med_font = pygame.font.SysFont("monospace", 32)
                self.small_font = pygame.font.SysFont("monospace", 24)
        else:
            self.big_font = pygame.font.SysFont("monospace", 64)
            self.med_font = pygame.font.SysFont("monospace", 32)
            self.small_font = pygame.font.SysFont("monospace", 24)

        self.stage = "relax"
        self._start_time = 0
        self.running = False
        self.binary_values: Tuple[int, int] = (0, 0)

    # --------------------------------------------------------------------- #
    def run(self) -> None:
        self.running = True
        self._start_time = time.time()
        self._set_stage("relax")
        while self.running:
            self.clock.tick(60)
            self._handle_events()
            self._update_stage()
            self._draw()
        if self._owns_display:
            pygame.display.quit()

    # ------------------------------------------------------------------ #
    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
                self.running = False

    def _update_stage(self) -> None:
        elapsed = time.time() - self._start_time

        if self.stage in ("relax", "flex"):
            if elapsed < self.stage_seconds:
                return

            if self.stage == "relax":
                self.controls.calibrate_relax()
                self._set_stage("flex")
                self._start_time = time.time()
                elapsed = 0.0
            else:  # stage == "flex"
                self.controls.calibrate_flex()
                self._set_stage("monitor")
                self._start_time = time.time()

        if self.stage == "monitor":
            if elapsed < 0.1:
                return
            self._start_time = time.time()
            vals = self.controls.get_data()
            self.binary_values = (int(round(vals[0])), int(round(vals[1])))

    def _set_stage(self, stage: str) -> None:
        self.stage = stage
        

    # ------------------------------------------------------------------ #
    def _draw(self) -> None:
        surface = self.scene
        surface.fill((8, 10, 16))
        elapsed = time.time() - self._start_time

        if self.stage == "relax":
            self._draw_stage_text(surface, "RELAX YOUR MUSCLE", elapsed)
        elif self.stage == "flex":
            self._draw_stage_text(surface, "FLEX YOUR MUSCLE", elapsed)
        else:
            self._draw_monitor(surface)

        target = self.screen or pygame.display.get_surface()
        if target is None:
            return
        scaled = pygame.transform.smoothscale(surface, target.get_size())
        target.blit(scaled, (0, 0))
        pygame.display.flip()

    def _draw_stage_text(self, surface: pygame.Surface, text: str, elapsed: float) -> None:
        remaining = max(0.0, self.stage_seconds - elapsed)
        countdown = f"Holding for {remaining:0.1f}s"
        prompt = self.big_font.render(text, True, (235, 235, 245))
        timer = self.med_font.render(countdown, True, (180, 180, 190))
        info = self.small_font.render("Stay on cue, ESC to exit", True, (120, 120, 130))

        rect = prompt.get_rect(center=(self.base_size[0] // 2, self.base_size[1] // 2 - 30))
        surface.blit(prompt, rect.topleft)
        timer_rect = timer.get_rect(center=(self.base_size[0] // 2, self.base_size[1] // 2 + 40))
        surface.blit(timer, timer_rect.topleft)
        info_rect = info.get_rect(center=(self.base_size[0] // 2, self.base_size[1] - 40))
        surface.blit(info, info_rect.topleft)

    def _draw_monitor(self, surface: pygame.Surface) -> None:
        header = self.big_font.render("CALIBRATION COMPLETE", True, (120, 200, 140))
        surface.blit(header, header.get_rect(center=(self.base_size[0] // 2, 80)).topleft)

        p1 = self.med_font.render(f"Player 1: {self.binary_values[0]}", True, (235, 235, 245))
        p2 = self.med_font.render(f"Player 2: {self.binary_values[1]}", True, (235, 235, 245))
        surface.blit(p1, p1.get_rect(center=(self.base_size[0] // 2, self.base_size[1] // 2 - 20)).topleft)
        surface.blit(p2, p2.get_rect(center=(self.base_size[0] // 2, self.base_size[1] // 2 + 40)).topleft)

        hint = self.small_font.render("Binary inputs update in real time (ESC to quit)", True, (160, 160, 170))
        surface.blit(hint, hint.get_rect(center=(self.base_size[0] // 2, self.base_size[1] - 40)).topleft)


def main() -> None:
    controls = Controls()
    Calibration(controls=controls).run()


if __name__ == "__main__":
    main()
