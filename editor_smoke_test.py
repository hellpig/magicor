#!/usr/bin/env python3
"""Automated checks for the Pygame Magicor level editor.

The test uses SDL's dummy video/audio drivers, so it does not open a visible
window. It exercises the model, all bundled levels, resource-backed brush
rendering, saving/reloading, undo, scrolling, and a short GUI render loop.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from magicor.editor.brushes import FireBrush, IceBrush, PlayerBrush, TubeBrush
from magicor.editor.core import EditorDocument
from magicor.editor.pygame_editor import EditorApp


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"


def all_levels() -> list[Path]:
    return sorted(
        path
        for path in (DATA / "levels").rglob("*.lvl")
        if not any(part.startswith("_test") for part in path.parts)
    )


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_model() -> None:
    document = EditorDocument(DATA)
    check((DATA / "brushes").is_file(), "data/brushes is missing")
    check(len(document.brushes) >= 25, f"only {len(document.brushes)} brushes loaded")

    missing_images = []
    for brush in document.brushes:
        resource = getattr(brush, "resource", None)
        if resource and document.resolver.find_image(resource) is None:
            missing_images.append(resource)
    check(not missing_images, f"brush images missing: {missing_images}")

    player = next(brush for brush in document.brushes if isinstance(brush, PlayerBrush))
    fire = next(brush for brush in document.brushes if isinstance(brush, FireBrush))
    ice = next(brush for brush in document.brushes if isinstance(brush, IceBrush) and brush.connect is None)
    tube = next(brush for brush in document.brushes if isinstance(brush, TubeBrush))

    document.change()
    check(document.apply_brush(1, 1, player), "player placement failed")
    check(document.apply_brush(2, 2, fire), "fire placement failed")
    check(document.apply_brush(3, 3, ice), "ice placement failed")
    tube.direction = "right"
    tube.id = "A"
    check(document.apply_brush(4, 4, tube), "tube placement failed")
    check(len(document.level.sprites) == 4, "wrong sprite count after placement")
    check(document.undo(), "undo failed")
    check(len(document.level.sprites) == 0, "undo did not restore level")

    document.change()
    document.apply_brush(1, 1, player)
    document.apply_brush(2, 2, fire)
    document.scroll(1, 0)
    positions = {(s.name, s.x, s.y) for s in document.level.sprites}
    check(("player", 2, 1) in positions, "horizontal scroll did not move player")
    check(("fire", 3, 2) in positions, "horizontal scroll did not move fire")

    document.set_level_property("title", "Editor smoke test")
    document.set_level_property("description", "Saved by the new editor")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "roundtrip.lvl"
        document.save_level(path)
        loaded = EditorDocument(DATA)
        loaded.load_level(path)
        check(loaded.level.title == "Editor smoke test", "title did not round-trip")
        check(loaded.level.description == "Saved by the new editor", "description did not round-trip")
        check(len(loaded.level.sprites) == 2, "sprites did not round-trip")


def test_all_levels_and_gui() -> None:
    levels = all_levels()
    check(len(levels) == 78, f"expected 78 playable levels, found {len(levels)}")
    app = EditorApp(DATA, headless=True)
    for level_path in levels:
        app.document.load_level(level_path)
        surface = app.render_level()
        check(surface.get_size() == (640, 576), f"bad render size for {level_path}")
        # Every known sprite should map to a palette brush.
        unknown = [s for s in app.document.level.sprites if app.document.brush_copy_for_sprite(s) is None]
        check(not unknown, f"unknown sprites in {level_path}: {unknown}")
    app.document.load_level(levels[0])
    app.run(max_frames=3)



def test_gui_interactions() -> None:
    app = EditorApp(DATA, headless=True)
    app.draw()
    player_index = next(
        i for i, brush in enumerate(app.document.brushes) if isinstance(brush, PlayerBrush)
    )
    app.select_brush(player_index)

    def point_for_cell(x: int, y: int) -> tuple[int, int]:
        return (
            app.map_rect.x + int((x + 0.5) * app.map_rect.width / 20),
            app.map_rect.y + int((y + 0.5) * app.map_rect.height / 18),
        )

    app.map_mouse_down(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": point_for_cell(5, 6), "button": 1}))
    app.map_mouse_up()
    player = app.document.sprite_at(5, 6)
    check(player is not None and player.name == "player", "GUI click did not place player")

    # Clicking the same type starts the original editor's drag-to-move behavior.
    app.map_mouse_down(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": point_for_cell(5, 6), "button": 1}))
    app.map_mouse_motion(pygame.event.Event(pygame.MOUSEMOTION, {"pos": point_for_cell(7, 8)}))
    app.map_mouse_up()
    check(app.document.sprite_at(7, 8) is player, "GUI drag did not move player")

    app.map_mouse_down(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": point_for_cell(7, 8), "button": 3}))
    check(app.selected_sprite is player, "right click did not select sprite")
    check(isinstance(app.sprite_edit_brush, PlayerBrush), "sprite properties did not load")
    app.sprite_edit_brush.direction = "left"
    app.apply_sprite_properties()
    check(player.args == "left", "sprite property apply failed")
    app.action_undo()
    restored = app.document.sprite_at(7, 8)
    check(restored is not None and restored.args == "right", "GUI undo did not restore property")
    pygame.quit()

def main() -> int:
    pygame.display.init()
    test_model()
    test_all_levels_and_gui()
    test_gui_interactions()
    print("Magicor editor smoke test passed.")
    print("- loaded the complete data-driven brush palette")
    print("- tested drawing, undo, scrolling, settings, and save/reload")
    print("- rendered all 78 playable levels")
    print("- ran the Pygame editor GUI for several headless frames")
    print("- tested click-to-place, drag-to-move, sprite editing, and GUI undo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
