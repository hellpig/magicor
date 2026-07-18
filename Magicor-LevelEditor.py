#!/usr/bin/env python3
"""Launch the Pygame Magicor level editor."""

from __future__ import annotations

import os
import sys


def change_to_project_directory() -> None:
    project_dir = os.path.abspath(os.path.dirname(__file__))
    os.chdir(project_dir)
    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)


change_to_project_directory()

from magicor.editor.pygame_editor import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
