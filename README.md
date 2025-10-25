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
pip install -r py-game/requirements.txt
```

### Run

```
python3 py-game/pong.py
```

If you see an error that `pygame` is missing, install it with `pip install pygame` or use the requirements above.
