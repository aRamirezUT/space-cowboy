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

## py-game/twin_suns_duel.py

High-tension binary duel under twin suns.

Rules
- Two inputs per player: 1 = Shoot (Attack), 0 = Deflect (Block)
- Attack if input > ATTACK_THRESHOLD; otherwise block (default).
- Shield drains only while blocking; you have 3 seconds total. When it hits 0, guard breaks and you can’t block anymore.
- You win by shooting when your opponent isn’t blocking.
- Simultaneous attacks cancel each other.

Keyboard
- Player 1: W to attack
- Player 2: Up Arrow to attack

Run
```
python3 py-game/twin_suns_duel.py
```

Config: `py-game/configs/twin_suns_duel.py`
- ATTACK_THRESHOLD: input > threshold => attack
- SHIELD_MAX_SECONDS: total blocking time
- Gauge sizes: INPUT_BAR_WIDTH_FRAC, INPUT_BAR_HEIGHT, SHIELD_BAR_HEIGHT
- Window: WINDOW_SCALE, FULLSCREEN_DEFAULT
- Colors: BG_COLOR, FG_COLOR, ACCENT, ALERT, WARNING
- Fonts: FONT_PATH

# Resources
## Pixel Art Generation
1. Background generation
   - [perchance](https://perchance.org/ai-pixel-art-generator)
2. Character creation
   - [pixellab](https://www.pixellab.ai/)
   - [google gemini](https://gemini.google.com/)
3. Background removal (make images transparent)
	- [photoroom](https://www.photoroom.com/tools/background-remover)
## Font
1. [OldblitzDemo](https://www.fontspace.com/)