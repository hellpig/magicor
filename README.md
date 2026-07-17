# Magicor! — The Cool Penguin Saves the World

A Python 3 and Pygame 2 port of **Magicor**, the puzzle-platform game originally created by Peter Gebauer.

Magicor is similar in spirit to *Solomon's Key*, but with its own mechanics. Push ice blocks into fires, create and destroy ice with magic, navigate tubes and hazards, and extinguish every fire to complete each level.

## Python 3 port

The original Magicor 1.1 release was written for Python 2 and an older version of Pygame. This repository updates the game to run with Python 3 and Pygame 2.

Changes include:

- conversion from Python 2 to Python 3;
- compatibility with Pygame 2 collision behavior;
- fixes for pushing ice blocks;
- fixes for entering horizontal and vertical tubes;
- preservation of integer behavior used for tile coordinates and animation frames;
- improved resource-path handling;
- updated audio initialization;
- a Windows launcher and automated smoke test.

The included level editor has **not** been fully ported because it depends on the obsolete PyGTK 2 stack. The game itself is the supported part of this port.

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

Install Python 3 and Pygame 2 using your distribution's package manager or pip, then run:

```bash
python3 -m pip install -r requirements.txt
python3 Magicor.py
```

## Gameplay

The goal is to extinguish every fire in each level by pushing ice blocks into it. Both the fire and the ice block are destroyed when they collide.

Ice blocks cannot be pushed when they are connected to a wall or another block, or when something blocks their movement. When a block cannot be pushed but is within climbing range, the penguin climbs onto it instead.

Unsupported ice blocks fall. Falling blocks can also extinguish fires. The penguin can create or destroy ice diagonally below itself, allowing gaps to be filled and supporting blocks to be removed.

Enemies, traps, lava, fire, and falling out of a level kill the player.

## Walkthroughs

A complete gameplay walkthrough playlist is available on YouTube:

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

## Testing

The Python 3 port was tested with Python 3.13 and Pygame 2.6.1.

Automated testing included:

- compiling all Python source files;
- starting the game and reaching the title screen;
- constructing and running all 78 included levels;
- scripted movement and action input;
- ice-pushing collision checks;
- horizontal and vertical tube-entry checks;
- loading all bundled sound and music files.

Because automated testing used SDL's headless display and audio modes, ordinary interactive testing on Windows and Linux is still valuable.

To run the included smoke test:

```bash
python smoke_test.py
```

## License

The original Magicor project and its content were released into the **public domain**. See [`LICENSE`](LICENSE) for the original dedication and full details.

