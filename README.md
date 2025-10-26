# space-cowboy

## py-game/pong.py

A simple two-player Pong game using pygame with alien spaceship players and template hooks for Bluetooth input.

Controls
- Player 1 spaceship: W (up) / S (down)
- Player 2 spaceship: Up / Down arrows

Bluetooth
- The functions `poll_ble_player1()` and `poll_ble_player2()` in `py-game/pong.py` are templates.
- Replace their bodies with non-blocking BLE polling (e.g., using bleak) and return:
	- `-1` for up, `0` for no input, `+1` for down.
- When BLE returns a non-zero value, it overrides keyboard input for that frame.

### Setup

Recommended: use a virtual environment.

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run

```
python3 py-game/pong.py
```

## py-game/quickdraw.py

Western quickdraw duel built on the same pygame helpers.

Rules
- Press SPACE/ENTER to arm the duel and start a 3-second countdown.
- After "DRAW!", the first player to input wins.
	- Keyboard: Player 1 uses W; Player 2 uses Up Arrow.
	- BLE: If wired in via `ControlsMixin.poll_ble()`, a non-zero transition after DRAW counts.
- Press R to restart, Q or ESC to quit, F11 to toggle fullscreen.

Sprites
- Uses specific holstered/drawn sprites:
	- `py-game/sprites/images/space-cowboy-holstered-east-facing.png`
	- `py-game/sprites/images/space-cowboy-holstered-west-facing.png`
	- `py-game/sprites/images/space-cowboy-drawn-east-facing.png`
	- `py-game/sprites/images/space-cowboy-drawn-west-facing.png`
	- Background: `py-game/sprites/images/western-background.png` (fallback to starfield if missing)

Run
```
python3 py-game/quickdraw.py
```

Config
- Tweak sizes/colors/placement in `py-game/configs/quickdraw.py`.
	- Vertical placement: `GROUND_FRAC` (0..1) for ground line, `FOOT_MARGIN_PX` gap from ground to boots.
	- Sprite size: `SHIP_HEIGHT_FRAC`, `SHIP_ASPECT_SCALE`, margins via `SHIP_MARGIN_FRAC`.
	- Window: `WINDOW_SCALE` for initial windowed size, `FULLSCREEN_DEFAULT` to start fullscreen or windowed.
 	- Text: `TEXT_OUTLINE_PX` (thickness) and `TEXT_OUTLINE_COLOR` (RGB) for outlined text borders.

# Resources
## Pixel Art Generation
1. Background generation
   - [perchance](https://perchance.org/ai-pixel-art-generator)
2. Character creation
   - [pixellab](https://www.pixellab.ai/)
   - [google gemini](https://gemini.google.com/)
## Font
1. [OldblitzDemo](https://www.fontspace.com/)