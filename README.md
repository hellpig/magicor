# Magicor! — The Cool Penguin Saves the World

A Python 3 and Pygame 2 port of **Magicor**, the puzzle-platform game originally created by Peter Gebauer.

The original Magicor 1.1 release was written for Python 2 and relied on behavior from older versions of Pygame. In particular, some collision checks no longer worked correctly under Pygame 2, so I used ChatGPT to make this port in 2026.

Magicor is similar in spirit to *Solomon's Key*, but with its own mechanics. Push ice blocks into fires, create and destroy ice with magic, navigate tubes and hazards, and extinguish every fire to complete each level.

## Python 3 port

This repository updates the game to run with Python 3 and Pygame 2.

Changes include:

- conversion from Python 2 to Python 3
- compatibility with Pygame 2 collision behavior
- fixes for pushing ice blocks
- fixes for entering horizontal and vertical tubes
- preservation of integer behavior used for tile coordinates and animation frames
- improved resource-path handling
- updated audio initialization
- Windows launchers and automated smoke tests
- added descriptions to many `.lvl` files
- corrected two apparent music-assignment mistakes in the level files
- replacement of the obsolete PyGTK 2 level editor with a simple Pygame editor
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

## Level editor

This repository includes a Python 3/Pygame 2 replacement for the original Magicor 1.1 PyGTK 2 level editor. It deliberately keeps the editor simple and follows the original editor's behavior where practical. PyGTK 2 is completely deprecated and no longer supported.

Run the editor from the repository root:

```bash
python Magicor-LevelEditor.py
```

To open a level immediately:

```bash
python Magicor-LevelEditor.py data/levels/forest/forest-01.lvl
```

The editor uses Pygame for its main window, palette, level display, and editing controls. Tkinter is used only for native open/save/resource file chooser dialogs. Tkinter is included with ordinary Python installations on Windows and the official macOS installer, and is available on most Unix-like systems, although some Linux distributions package it separately. If Tkinter is unavailable, those chooser operations report that they could not open.

The editor uses `data/brushes` and the existing `data/levels/*/brushes` files to construct its palette. The old `data/editor/magicor-editor.glade*` files are not used, so they were deleted.

### Editing

- Select a brush in the left palette.
- Left-click or drag on the level to paint.
- Click a sprite to select it, then click elsewhere to move it.
- Holding **Shift** while dragging also moves an existing sprite.
- Right-click a sprite to edit its properties in the right panel.
- The erase brush removes the tile and any sprites overlapping that cell.
- Background and music may be entered as resource names or selected with the `...` buttons.

Toolbar buttons provide new, open, save, save as, undo, grid, wraparound scrolling, and a basic level check. The basic level check verifies that the level has exactly one player and that every placed sprite has a matching editor brush.

Keyboard shortcuts:

- `Ctrl+N`: new
- `Ctrl+O`: open
- `Ctrl+S`: save
- `Ctrl+Shift+S`: save as
- `Ctrl+Z`: undo
- `Ctrl+G`: toggle grid
- `Alt+Arrow`: wrap the level one cell
- `Delete`: delete the selected sprite
- `Escape`: cancel text editing or clear sprite selection
- `F5`: run the basic level check

The game discovers `.lvl` files recursively inside `data/levels/`. Folders beginning with `_` are hidden unless developer mode is enabled. The title stored inside the level, rather than merely the filename, affects its display order.

The editor differs from the original in a few practical ways:

- The main window, palette, settings, and sprite options are drawn in one Pygame window instead of separate GTK dialogs.
- Window-position preferences and the obsolete `magicor-editor.conf` are not used.
- Undo is functional for ordinary editing operations. The original source had an undo stack and menu item, but its GTK frontend did not contain an `on_undo` handler and did not record normal drawing edits.
- Description and hint fields are exposed because the existing level format already supports them.

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

Pygame is the only third-party Python package required. The editor's optional native file choosers use Tkinter, which normally comes with the standard Windows Python installer.

### Linux and other Unix-like systems

Install Python 3, then install the required Python package and run the game:

```bash
python3 -m pip install -r requirements.txt
python3 Magicor.py
```

Tkinter is available on most Unix-like systems but may be packaged separately by your distribution. It is needed only for the editor's native file chooser dialogs, not for running the game or using the rest of the editor.

## Main programs and Windows launchers

The two main programs are:

- `Magicor.py` — the game
- `Magicor-LevelEditor.py` — the level editor

Windows users can also use four batch-file launchers:

- `run-magicor.bat` — run the game with a console available for error messages
- `run-magicor-no-console.bat` — run the game without a console window
- `run-magicor-editor.bat` — run the editor with a console available for error messages
- `run-magicor-editor-no-console.bat` — run the editor without a console window

The regular console launchers are more useful when diagnosing a startup error.

## Testing

The Python 3 port was tested with Python 3.13 and Pygame 2.6.1.

Automated game testing included:

- compiling all Python source files
- starting the game and reaching the title screen
- constructing and running all 78 included levels
- scripted movement and action input
- ice-pushing collision checks
- horizontal and vertical tube-entry checks
- loading all bundled sound and music files

Because automated testing used SDL's headless display and audio modes, ordinary interactive testing on Windows and Linux is still valuable.

To run the game smoke test:

```bash
python smoke_test.py
```

The game smoke test is primarily a developer verification tool, not something players need to run. Its purpose is to catch broad regressions quickly—for example, if a future code edit breaks level parsing, resource paths, tubes, ice, or audio loading. It is optional. It documents and repeatedly verifies the two most important Pygame 2 compatibility fixes.

To run the editor smoke test:

```bash
python editor_smoke_test.py
```

The editor smoke test checks the data-driven palette, drawing, erase/movement-related model operations, undo, wraparound scrolling, settings, save/reload, sprite property editing, all 78 playable levels, and several GUI frames.

The editor test cannot replace ordinary interactive use, especially native file dialogs and detailed mouse interaction on Windows.

## License

The original Magicor project and its content were dedicated to the **public domain**. This port preserves the original [`LICENSE`](LICENSE) file and licensing terms.
