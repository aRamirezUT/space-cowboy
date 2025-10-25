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
- Both players use `py-game/sprites/images/western-cowboy.png`.

Run
```
python3 py-game/quickdraw.py
```
