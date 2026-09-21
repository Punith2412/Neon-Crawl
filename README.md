# NeonCrawl

A neon-styled Snake game built with Python and Tkinter. It adds lives, levels, combos, weighted food types, collectible power-ups and particle effects on top of classic Snake.

<!-- Add a screenshot: save it as screenshot.png in this folder, then uncomment the line below -->
<!-- ![NeonCrawl gameplay](screenshot.png) -->

## Features

- 3 lives per game
- Level system: speed increases every 120 points
- Combo multiplier for eating food in quick succession
- 4 food types with different point values and spawn chances
- 4 power-ups you collect and use on demand
- Particle explosions, glowing food and floating score text
- High score saved between sessions
- Pause, quit and restart controls

## Requirements

- Python 3.8 or newer
- Tkinter (included with most Python installs)
  - On Debian/Ubuntu, if it's missing: `sudo apt install python3-tk`

No third-party packages are needed.

## Run

```bash
python Snake.py
```

Run it from the folder that contains `Snake.py` so the high score file is created and read in the right place.

## Controls

| Key | Action |
|---|---|
| Arrow keys / WASD | Move |
| Enter | Start game / continue after losing a life / resume |
| Space | Use a collected power-up |
| P | Pause / resume |
| Esc | Save high score and quit |

## Gameplay

### Food

| Food | Points | Spawn chance | Growth |
|---|---|---|---|
| Apple | 10 | 65% | +2 |
| Gold | 25 | 22% | +3 |
| Crystal | 50 | 8% | +4 |
| Heart | 100 | 5% | +5 |

### Combo

Eating food within 3 seconds of the last one raises your combo. Each combo step adds 10% to the points for that food. The combo resets if the timer runs out.

### Levels and speed

Level = `score // 120 + 1`. The snake starts at 195 ms per step, gets 17 ms faster each level, and stops speeding up at 55 ms.

### Power-ups

A power-up appears on the board roughly every 12 seconds. Drive over it to store it in your inventory, then press Space to use it.

| Power-up | Effect | Duration |
|---|---|---|
| Slow | Slows the snake down | 8 s |
| x2 Pts | Doubles points from food | 7 s |
| Shield | Survive one hit on your own body | 5 s |
| Shrink | Cuts the snake to half its length (minimum 3 segments) | Instant |

### Losing

Hitting a wall or your own body costs one life. After the last life, the game-over screen shows your final score, best score and level reached.

## Project structure

```
.
├── Snake.py          # The whole game
├── highscore.json    # Best score, created and updated automatically
└── README.md
```

## How it works

- **Grid model:** the snake is a list of `(x, y)` grid cells. The head is at index 0.
- **Movement:** each step inserts a new head cell and removes the tail cell, unless the snake is growing.
- **Game loop:** `_tick` runs about every 16 ms (~60 fps). It calls `_update` (timers, animations, movement) while playing, then always calls `_draw`.
- **Movement timing:** `_update` adds elapsed time to an accumulator and calls `_step` once it passes the current speed. Rendering and game speed are independent.
- **State machine:** `START`, `PLAY`, `PAUSE` and `DEAD`.
- **Input safety:** key presses set a queued direction (`ndir`). The real direction (`dir`) only updates inside `_step`, and 180° reversals are blocked, so fast key presses can't make the snake turn back into itself.
- **Rendering:** the canvas is cleared and every element is redrawn each frame. Snake colors blend along a gradient from head to tail.

## Known issues

- Pressing Space can activate a power-up that is still lying on the board, because uncollected and collected power-ups share one list.
- The "Max Combo" value on the game-over screen shows the current combo, not the highest one reached.
- Shield only protects against hitting your own body, not the walls.

## Author

Punith Kumar Patil — [github.com/Punith2412](https://github.com/Punith2412)
