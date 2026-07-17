# Magicor! — The Cool Penguin Saves the World

A Python 3 and Pygame 2 port of **Magicor**, the puzzle-platform game originally created by Peter Gebauer.

The original Magicor 1.1 release was written for Python 2 and relied on behavior from older versions of Pygame. In particular, some collision checks no longer worked correctly under Pygame 2, so I used ChatGPT to make this port in 2026.

Magicor is similar in spirit to *Solomon's Key*, but with its own mechanics. Push ice blocks into fires, create and destroy ice with magic, navigate tubes and hazards, and extinguish every fire to complete each level.

## Python 3 port

The original Magicor 1.1 release was written for Python 2 and an older version of Pygame. This repository updates the game to run with Python 3 and Pygame 2.

Changes include:

- conversion from Python 2 to Python 3
- compatibility with Pygame 2 collision behavior
- fixes for pushing ice blocks
- fixes for entering horizontal and vertical tubes
- preservation of integer behavior used for tile coordinates and animation frames
- improved resource-path handling
- updated audio initialization
- a Windows launcher and automated smoke test
- added descriptions to many `.lvl` files
- corrected two apparent music-assignment mistakes in the level files
- removal of the level editor, which depends on the obsolete PyGTK 2 stack
- removal of the original installation scripts and instructions, because this version is intended to be a lightweight, portable, clone-and-run game

I chose not to provide detailed installation scripts for every operating system. Instead, users are expected to be cool enough to install Python and the required package using the normal method for their system.

On non-Windows systems, the game stores settings and completion records in `~/.magicor/magicor.conf`. This is the one exception to the game being fully self-contained within its project folder. The code could easily be changed to store `magicor.conf` in the launch directory on every operating system, as it already does by default on Windows.

## Gameplay

The goal is to extinguish every fire in each level by pushing ice blocks into it. Both the fire and the ice block are destroyed when they collide.

Ice blocks cannot be pushed when they are connected to a wall or another block, or when something blocks their movement. When a block cannot be pushed but is within climbing range, the penguin climbs onto it instead.

Unsupported ice blocks fall. Falling blocks can also extinguish fires. The penguin can create or destroy ice diagonally below itself, allowing gaps to be filled and supporting blocks to be removed.

Enemies, traps, lava, fire, and falling out of a level kill the player.

## Walkthroughs

I made a complete walkthrough playlist on YouTube:

[Magicor walkthrough playlist](https://www.youtube.com/playlist?list=PLZr9Wbtug46at5jhAICo6ctHJzpMeWXmH)

## Original project

Magicor was originally released by Peter Gebauer on SourceForge:

- [Original Magicor website](https://magicor.sourceforge.net/)
- [Original download page](https://magicor.sourceforge.net/download.shtml)
- [Original SourceForge files](https://sourceforge.net/projects/magicor/files/)

The original README credits:

- **Peter Gebauer** — original creator
- **Frederic Wagner** — Debian packages, levels, and bug fixes
- **Claudio Canepa** — Windows compatibility, levels, and bug fixes

The original artwork was made with GIMP. The original documentation also thanks the Python, SDL, Pygame, GNU, and Debian communities, Michael Krause for SoundTracker, and Danc of Lost Garden for free textures.

## Installation

### Windows

1. Install a current version of [Python 3](https://www.python.org/downloads/).
2. Download or clone this repository.
3. Open a terminal in the project folder.
4. Install Pygame:

   ```bash
   python -m pip install -r requirements.txt
   ```

5. Run the game:

   ```bash
   python Magicor.py
   ```

You can also double-click `run-magicor.bat` after Python and Pygame are installed.

### Linux

Install Python 3, then install the required Python package and run the game:

```bash
python3 -m pip install -r requirements.txt
python3 Magicor.py
```

## Testing

The Python 3 port was tested with Python 3.13 and Pygame 2.6.1.

Automated testing included:

- compiling all Python source files
- starting the game and reaching the title screen
- constructing and running all 78 included levels
- scripted movement and action input
- ice-pushing collision checks
- horizontal and vertical tube-entry checks
- loading all bundled sound and music files

Because automated testing used SDL's headless display and audio modes, ordinary interactive testing on Windows and Linux is still valuable.

To run the included smoke test:

```bash
python smoke_test.py
```

The smoke test is primarily a developer verification tool, not something players need to run. Its purpose is to catch broad regressions quickly—for example, if a future code edit breaks level parsing, resource paths, tubes, ice, or audio loading. It is optional. It documents and repeatedly verifies the two most important Pygame 2 compatibility fixes.

## License

The original Magicor project and its content were dedicated to the **public domain**. This port preserves the original [`LICENSE`](LICENSE) file and licensing terms.
