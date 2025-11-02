# Space Cowboy 🤠

**MYO BEBOP**: A suite of retro-style pygame games designed for dual input control via keyboard or EMG sensors through BLE connectivity.

## 🎮 Quick Start

### Setup
```bash
# Clone the repository
git clone https://github.com/aRamirezUT/space-cowboy.git
cd space-cowboy

# Create a conda environment (required for BLE)
conda activate base

# Install required packages
conda install conda-forge::liblsl
conda install conda-forge::pip

# Install dependencies
pip install -r requirements.txt
```

### Launch Menu
```bash
python3 main.py
```

## 🎯 Games

### 1. Quickdraw Duel
*Western-themed timing dueling game*

**Objective**: Be the first to draw after "DRAW!" appears
- Press `SPACE/ENTER` to start countdown: READY → Set → (random delay) → DRAW!
- First valid input after "DRAW!" wins
- Drawing too early results in a foul and automatic loss

**Controls**:
- Player 1: `W` key
- Player 2: `Up Arrow`

**Assets**: Uses detailed cowboy sprites with holstered/drawn poses

---

### 2. Twin Suns Duel  
*High-tension binary combat with resource management*

**Objective**: Defeat opponent by attacking when they can't block
- **Attack** (input > threshold): Shoot at opponent  
- **Block** (input ≤ threshold): Deflect incoming attacks
- Shield energy drains while blocking (3 seconds total)
- When shield depletes, guard breaks and you become vulnerable
- Simultaneous attacks cancel each other

**Strategy**: Balance offense with shield conservation

---

### 3. Pong
*Classic arcade game with alien spaceship paddles*

**Objective**: Score points by getting the asteroid past opponent's paddle
- First to reach the score limit wins
- Asteroid speed increases after each rally
- Uses alien saucer sprites for paddles

**Controls**:
- Player 1: `W` (up) / `S` (down)  
- Player 2: `Up/Down Arrows`

---

### 4. Calibration
*EMG sensor setup and testing utility*

**Purpose**: Configure EMG thresholds for optimal gameplay
- **Relax Phase**: Sets baseline EMG levels (5 seconds)
- **Flex Phase**: Sets activation thresholds (5 seconds)  
- **Monitor Phase**: Real-time binary input display

**Essential for EMG users**: Ensures accurate muscle signal detection

## 🎛️ Control Systems

### Keyboard Controls
- **Player 1**: `W` key (primary action)
- **Player 2**: `Up Arrow` (primary action)
- **Universal**: 
  - `R`: Restart game
  - `Q/ESC`: Quit
  - `F11`: Toggle fullscreen
  - `SPACE/ENTER`: Start/Select

### EMG/BLE Controls
- **Flex**: Action/Attack (binary 1)
- **Relax**: Block/Default (binary 0)
- Requires calibration before first use
- Automatically overrides keyboard when active

## 🏗️ Project Structure

```
space-cowboy/
├── main.py                 # Main menu launcher
├── requirements.txt        # Python dependencies
├── src/
│   ├── games/             # Game implementations
│   │   ├── base_game.py   # Shared game functionality
│   │   ├── quickdraw.py   # Western duel game
│   │   ├── twin_suns_duel.py # Binary combat game
│   │   ├── pong.py        # Classic paddle game
│   │   └── calibration.py # EMG setup utility
│   ├── controls/          # Input handling
│   │   ├── controls.py    # Unified keyboard/EMG interface
│   │   └── exg/           # EMG signal processing
│   │       ├── ble_server.py    # BLE communication
│   │       ├── exg_client.py    # Signal acquisition
│   │       └── filtering/       # Signal filters (EMA, IIR, SMA)
│   ├── sprites/           # Visual assets
│   │   ├── player.py      # Player sprite class
│   │   ├── Asteroid.py    # Ball/projectile sprite
│   │   ├── background.py  # Starfield generation
│   │   └── images/        # Sprite artwork
│   ├── fonts/             # Typography system
│   │   ├── fonts.py       # Font loading utilities
│   │   └── HerculesPixelRegular/ # Pixel art font
│   └── configs/           # Game-specific settings
│       ├── main.py        # Shared configuration
│       ├── pong.py        # Pong parameters
│       ├── quickdraw.py   # Quickdraw parameters
│       └── twin_suns_duel.py # Duel parameters
```

## 🎨 Assets

### Sprites
- **Cowboys**: Holstered/drawn poses (east/west facing)
- **Combat**: Blaster/shield variants for Twin Suns
- **Space**: Alien saucer, asteroid, western background
- **Format**: PNG with transparency support

### Fonts  
- **Primary**: Hercules Pixel Regular (retro pixel art style)
- **Fallback**: System monospace fonts

### Graphics
All sprites are pixel art optimized for 960x540 base resolution with scaling support.

## ⚙️ Configuration

Each game has dedicated configuration files in `src/configs/`:
- **Window settings**: Resolution, scaling, fullscreen defaults
- **Gameplay parameters**: Speed, thresholds, timing
- **Visual styling**: Colors, margins, UI layout
- **Input mapping**: Key bindings, EMG thresholds

Example customization:
```python
# src/configs/quickdraw.py
PLAYER_HEIGHT_FRAC = 0.48    # Cowboy size relative to screen
GROUND_FRAC = 1.0            # Ground line position  
COUNTDOWN_TOTAL = 3000       # Milliseconds for ready sequence
```

## 🔬 EMG Integration

### Hardware Requirements
- Compatible EMG sensors (MYO BEBOP)
- BLE connectivity
- LSL (Lab Streaming Layer) support

### Signal Processing Pipeline
1. **Acquisition**: Raw EMG via BLE streaming
2. **Filtering**: EMA/IIR noise reduction  
3. **Calibration**: Personalized flex/relax thresholds
4. **Binary Classification**: Real-time muscle state detection

### Usage
1. Enable `BLE_ENABLED = True` in `src/controls/controls.py`
2. Run calibration before gaming sessions
3. System automatically switches to EMG when available

## 🛠️ Development

### Dependencies
- **pygame**: Game engine and graphics
- **numpy**: Signal processing
- **bleak**: BLE communication  
- **pylsl**: Lab Streaming Layer
- **scipy**: Advanced filtering

### Architecture
- **Modular design**: Shared base classes and utilities
- **Configuration-driven**: Easy gameplay tuning
- **Dual input support**: Seamless keyboard/EMG switching  
- **Scalable rendering**: Fixed logical resolution with display scaling

## 🎯 Resources

### Pixel Art Creation
- [Perchance AI Generator](https://perchance.org/ai-pixel-art-generator) - Backgrounds
- [PixelLab AI](https://www.pixellab.ai/) - Character sprites
- [Google Gemini](https://gemini.google.com/) - Asset generation
- [PhotoRoom](https://www.photoroom.com/tools/background-remover) - Background removal

### Typography
- [FontSpace](https://www.fontspace.com/) - Pixel art fonts

---

**Built for MYO BEBOP EMG Gaming Platform** 🚀

## py-game/quickdraw.py

Western quickdraw duel built on the same pygame helpers.

Rules
- Press SPACE/ENTER to arm the duel and start a 3-second countdown.
- After "DRAW!", the first player to input wins.
	- Keyboard: Player 1 uses W; Player 2 uses Up Arrow.
	- BLE: If wired in via `Controls.poll_ble()`, a non-zero transition after DRAW counts.
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