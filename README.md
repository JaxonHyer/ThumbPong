# ThumbPong

A vibrant, full-color Pong remake built specifically for the **TinyCircuits Thumby Color** (`128×128` 16-bit RGB565 display, RP2350 MicroPython OS).

## Features

- **3 Game Modes**
  - **1P VS AI**: Classic Pong against 4 AI difficulty levels (`EASY`, `NORM`, `HARD`, `ACE`).
  - **2P LOCAL**: Two-player head-to-head on a single Thumby Color (`D-Pad` vs `A/B`).
  - **ARCADE**: Fast-paced color Pong with collectible arena power-up orbs:
    - `B` **Big Paddle** (Green) — Enlarges your paddle.
    - `S` **Shrink Foe** (Orange) — Shrinks your opponent's paddle.
    - `M` **Multiball** (Cyan) — Splits play into up to 3 active balls.
    - `F` **Fire Shot** (Yellow) — Supercharges ball speed with a golden trail.
    - `W` **Shield Wall** (Magenta) — Places a 1-hit barrier behind your goal.
- **5 Curated Color Themes**: `NEON`, `SUNSET`, `CYBER`, `FIRE&ICE`, and `CHROMA` (live-switchable with `LB` / `RB` on the title screen or in Options/Pause).
- **Skill Mechanics**: Paddle velocity spin transfer, **Dash** (`A`/`RB` held), and timed **Power Smash** (`A`/`RB` pressed on impact) with screen shake and sparks.
- **Full Thumby Color Hardware Integration**:
  - **128×128 RGB565** rendering with fading ball trails, heat-reactive ball colors, hit flashes, and confetti.
  - **4-channel WAV SFX** (`engine_audio` + `WaveSoundResource`) with custom 8-bit chiptune sound effects.
  - **Haptic Rumble** (`engine_io.rumble`) on hits, smashes, power-ups, and goals.
  - **Front RGB LED** (`engine_io.indicator`) reactive flashes on goals and power-ups (cleanly restored on exit).
  - **Persistent Saves** (`engine_save`) for Best Rally, Wins, and preferences.
- **Thumby Color OS Launcher Ready**: Includes `manifest.ini` and a custom `38×38` 16-bit RGB565 `icon.bmp`.

## Controls

### Title & Menus
- **D-Pad Up / Down**: Navigate menu
- **D-Pad Left / Right** or **A**: Change option / Confirm
- **LB / RB** (Title Screen): Cycle color theme live
- **B** or **MENU**: Back / Exit to Thumby Color OS

### 1P VS AI & Arcade
- **D-Pad Up / Down**: Move paddle
- **Hold A** or **RB**: Dash (faster paddle movement)
- **Press A** or **RB** at impact: **Power Smash**
- **MENU**: Pause menu

### 2P Local
- **Player 1 (Left)**: **D-Pad Up / Down** (`LB` to Smash)
- **Player 2 (Right)**: **A** (Up) / **B** (Down) (`RB` to Smash)
- **MENU**: Pause menu

## Installing on Thumby Color

1. Connect your Thumby Color via USB-C and open **Thonny IDE** (with MicroPython Raspberry Pi Pico interpreter) or the **Thumby Color Code Editor**.
2. Copy the contents of this repository into `/Games/ThumbPong/` on your Thumby Color filesystem:
   - `manifest.ini`
   - `main.py`
   - `icon.bmp`
   - `themes.py`
   - `storage.py`
   - `audio_haptics.py`
   - `pong_engine.py`
   - `renderer.py`
   - `sfx/` (all `.wav` files)
3. Reboot or return to the Thumby Color OS launcher — **ThumbPong** will appear under **Games** with its custom color icon.

## Running Tests Locally

A unit & simulation test suite (with mocked `engine_*` modules and binary asset validators for `icon.bmp` and `sfx/*.wav`) is included:

```bash
python3 -m unittest discover -s tests -v
```
