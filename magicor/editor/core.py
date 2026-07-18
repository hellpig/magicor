"""Editor model and resource helpers for the Pygame Magicor level editor."""

from __future__ import annotations

import copy
import math
import os
from pathlib import Path
from typing import Iterable, Optional

from magicor.level import Level, LevelSprite
from magicor.editor.brushes import (
    Brush,
    ClimbingEnemyBrush,
    DecorationBrush,
    DEFAULT_BRUSH_FACTORIES,
    DirectionBrush,
    EraseBrush,
    FireBrush,
    IceBrush,
    LavaBrush,
    PlayerBrush,
    ResourceBrush,
    SpriteBrush,
    StationaryEnemyBrush,
    TileBrush,
    TrapolaBrush,
    TubeBrush,
    WalkingEnemyBrush,
)


class EditorError(Exception):
    """A user-facing editor error."""


class ResourceResolver:
    IMAGE_SUFFIXES = ("png", "jpg", "jpeg", "gif")
    MUSIC_SUFFIXES = ("ogg", "mp3", "mod", "xm")
    SOUND_SUFFIXES = ("wav", "au")

    def __init__(self, data_path: str | os.PathLike[str]) -> None:
        self.data_path = Path(data_path).expanduser().resolve()

    @property
    def search_roots(self) -> list[Path]:
        return [self.data_path, self.data_path / "levels"]

    def find(self, resource: Optional[str], suffixes: Iterable[str]) -> Optional[Path]:
        if not resource:
            return None
        normalized = resource.replace("\\", "/").strip("/")
        parts = normalized.split("/")
        alternatives = [normalized]
        if parts:
            alt_parts = parts[:-1] + ["_" + parts[-1]]
            alternatives.append("/".join(alt_parts))
        for root in self.search_roots:
            for name in alternatives:
                for suffix in suffixes:
                    candidate = root / f"{name}.{suffix.lstrip('.')}"
                    if candidate.is_file():
                        return candidate
        return None

    def find_image(self, resource: Optional[str]) -> Optional[Path]:
        return self.find(resource, self.IMAGE_SUFFIXES)

    def find_music(self, resource: Optional[str]) -> Optional[Path]:
        return self.find(resource, self.MUSIC_SUFFIXES)

    def find_sound(self, resource: Optional[str]) -> Optional[Path]:
        return self.find(resource, self.SOUND_SUFFIXES)

    def brush_files(self) -> list[Path]:
        files: list[Path] = []
        root = self.data_path / "brushes"
        if root.is_file():
            files.append(root)
        levels = self.data_path / "levels"
        if levels.is_dir():
            for directory in sorted(levels.iterdir(), key=lambda p: p.name.lower()):
                brush_file = directory / "brushes"
                if directory.is_dir() and not directory.name.startswith(".") and brush_file.is_file():
                    files.append(brush_file)
        return files


class EditorDocument:
    VERSION = "2.0-pygame"

    def __init__(self, data_path: str | os.PathLike[str], max_undos: int = 32) -> None:
        self.resolver = ResourceResolver(data_path)
        self.max_undos = max(1, int(max_undos))
        self.level = Level()
        self.saved_path: Optional[Path] = None
        self.undo_stack: list[Level] = []
        self.dirty = False
        self.brushes = self._make_brushes()
        self.brush_by_key = {self.brush_key_for_brush(brush): brush for brush in self.brushes}

    def _make_brushes(self) -> list[Brush]:
        brushes = [factory() for factory in DEFAULT_BRUSH_FACTORIES]
        for path in self.resolver.brush_files():
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                raise EditorError(f"Could not read brush file {path}: {exc}") from exc
            brushes.extend(self.parse_brushes(text))
        # The original GTK frontend silently omitted palette brushes whose image
        # resource was absent. Magicor 1.1 ships one such stale entry
        # (pompei/tile-vmosaic), so preserve that behavior here.
        return [
            brush
            for brush in brushes
            if not isinstance(brush, ResourceBrush)
            or self.resolver.find_image(brush.resource) is not None
        ]

    @staticmethod
    def parse_brushes(data: str) -> list[Brush]:
        result: list[Brush] = []
        for raw_line in data.replace("\r", "").split("\n"):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            try:
                if len(parts) == 2 and parts[0] == "tile":
                    result.append(TileBrush(parts[1]))
                elif len(parts) == 4 and parts[0] == "walking-enemy":
                    result.append(WalkingEnemyBrush(parts[1], parts[2], "right", int(parts[3])))
                elif len(parts) == 4 and parts[0] == "climbing-enemy":
                    result.append(ClimbingEnemyBrush(parts[1], parts[2], "up", int(parts[3])))
                elif len(parts) == 4 and parts[0] == "stationary-enemy":
                    result.append(StationaryEnemyBrush(parts[1], parts[2], "up", int(parts[3])))
                elif len(parts) == 4 and parts[0] == "decoration":
                    result.append(DecorationBrush(parts[1], int(parts[2]), int(parts[3]), 8))
            except ValueError as exc:
                raise EditorError(f"Invalid brush line: {raw_line!r}") from exc
        return result

    @staticmethod
    def brush_key(name: str, args: Optional[str]) -> str:
        if name == "ice":
            return f"ice {args}" if args else "ice"
        if name.endswith("-enemy"):
            parts = (args or "").split()
            if len(parts) >= 3:
                return f"{name} {parts[1]} {parts[2]}"
        if name == "decoration":
            parts = (args or "").split()
            if parts:
                return f"decoration {parts[0]}"
        return name

    @classmethod
    def brush_key_for_brush(cls, brush: Brush) -> str:
        if isinstance(brush, TileBrush):
            return f"tile {brush.resource}"
        if isinstance(brush, IceBrush):
            return f"ice {brush.connect}" if brush.connect else "ice"
        if isinstance(brush, (WalkingEnemyBrush, ClimbingEnemyBrush, StationaryEnemyBrush)):
            return brush.id
        if isinstance(brush, DecorationBrush):
            return f"decoration {brush.resource}"
        if isinstance(brush, SpriteBrush):
            return brush.name
        if isinstance(brush, EraseBrush):
            return "erase"
        return brush.__class__.__name__

    def brush_copy_for_sprite(self, sprite: LevelSprite) -> Optional[SpriteBrush]:
        original = self.brush_by_key.get(self.brush_key(sprite.name, sprite.args))
        if not isinstance(original, SpriteBrush):
            return None
        brush = original.copy()
        brush.update(sprite.args)
        return brush

    def _remember(self) -> None:
        self.undo_stack.append(copy.deepcopy(self.level))
        if len(self.undo_stack) > self.max_undos:
            del self.undo_stack[: len(self.undo_stack) - self.max_undos]

    def change(self) -> None:
        self._remember()
        self.dirty = True

    def undo(self) -> bool:
        if not self.undo_stack:
            return False
        self.level = self.undo_stack.pop()
        self.dirty = True
        return True

    def new_level(self) -> None:
        self.change()
        self.level = Level()
        self.saved_path = None

    def load_level(self, filename: str | os.PathLike[str]) -> None:
        path = Path(filename).expanduser().resolve()
        try:
            data = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise EditorError(f"Could not open {path}: {exc}") from exc
        self.change()
        self.level = Level(data)
        self.saved_path = path
        self.dirty = False

    def save_level(self, filename: str | os.PathLike[str] | None = None) -> Path:
        path = Path(filename).expanduser().resolve() if filename else self.saved_path
        if path is None:
            raise EditorError("No filename has been selected.")
        output = f"# Generated by Magicor-LevelEditor {self.VERSION}\n{self.level}\n"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(output, encoding="utf-8", newline="\n")
        except OSError as exc:
            raise EditorError(f"Could not save {path}: {exc}") from exc
        self.saved_path = path
        self.dirty = False
        return path

    def sprite_bounds(self, sprite: LevelSprite) -> tuple[int, int, int, int]:
        brush = self.brush_copy_for_sprite(sprite)
        if brush is None:
            return sprite.x, sprite.y, 1, 1

        # The player's artwork extends 16 pixels into the tile above, but its
        # logical level position is only the single tile containing its feet.
        if isinstance(brush, PlayerBrush):
            return sprite.x, sprite.y, 1, 1

        width = max(1, math.ceil(brush.width / 32.0))
        height = max(1, math.ceil(brush.height / 32.0))
        return sprite.x, sprite.y, width, height

    def sprites_at(self, x: int, y: int) -> list[LevelSprite]:
        found: list[LevelSprite] = []
        for sprite in self.level.sprites:
            sx, sy, width, height = self.sprite_bounds(sprite)
            if sx <= x < sx + width and sy <= y < sy + height:
                found.append(sprite)
        return found

    def sprite_at(self, x: int, y: int) -> Optional[LevelSprite]:
        sprites = self.sprites_at(x, y)
        return sprites[-1] if sprites else None

    def erase_at(self, x: int, y: int) -> bool:
        changed = False
        if self.level[x, y] is not None:
            self.level[x, y] = None
            changed = True
        for sprite in list(self.sprites_at(x, y)):
            self.level.sprites.remove(sprite)
            changed = True
        return changed

    def apply_brush(self, x: int, y: int, brush: Brush) -> bool:
        if not (0 <= x < self.level.width and 0 <= y < self.level.height):
            return False
        if isinstance(brush, EraseBrush):
            return self.erase_at(x, y)
        if isinstance(brush, TileBrush):
            value = str(brush)
            if self.level[x, y] == value:
                return False
            self.level[x, y] = value
            return True
        if isinstance(brush, SpriteBrush):
            if isinstance(brush, PlayerBrush):
                self.level.sprites[:] = [s for s in self.level.sprites if s.name != "player"]
            else:
                for sprite in list(self.sprites_at(x, y)):
                    if sprite.name == brush.name:
                        self.level.sprites.remove(sprite)
            parts = str(brush).split(" ", 1)
            args = parts[1] if len(parts) == 2 else None
            self.level.sprites.append(LevelSprite(x, y, parts[0], args))
            self.level.sprites.sort(key=lambda s: (getattr(s, "_sort", 99999), s.x, s.y))
            return True
        return False

    def move_sprite(self, sprite: LevelSprite, x: int, y: int) -> bool:
        x = max(0, min(self.level.width - 1, x))
        y = max(0, min(self.level.height - 1, y))
        if sprite.x == x and sprite.y == y:
            return False
        sprite.x = x
        sprite.y = y
        return True

    def update_sprite(self, sprite: LevelSprite, brush: SpriteBrush) -> None:
        parts = str(brush).split(" ", 1)
        sprite.name = parts[0]
        sprite.args = parts[1] if len(parts) == 2 else None
        try:
            sprite._sort = ("player", "lava", "decoration", "ice", "fire", "tube").index(sprite.name)
        except ValueError:
            sprite._sort = 99999
        self.level.sprites.sort(key=lambda s: (getattr(s, "_sort", 99999), s.x, s.y))

    def set_level_property(self, name: str, value: object) -> bool:
        old = getattr(self.level, name)
        if old == value:
            return False
        self.change()
        setattr(self.level, name, value)
        return True

    def scroll(self, dx: int, dy: int) -> None:
        if not dx and not dy:
            return
        self.change()
        width, height = self.level.width, self.level.height
        new_tiles = [[None] * width for _ in range(height)]
        for y in range(height):
            for x in range(width):
                new_tiles[(y + dy) % height][(x + dx) % width] = self.level[x, y]
        self.level.tiles = new_tiles
        for sprite in self.level.sprites:
            sprite.x = (sprite.x + dx) % width
            sprite.y = (sprite.y + dy) % height

    def validate(self) -> list[str]:
        issues: list[str] = []
        players = [sprite for sprite in self.level.sprites if sprite.name == "player"]
        if len(players) == 0:
            issues.append("Level has no player.")
        elif len(players) > 1:
            issues.append("Level has more than one player.")
        for sprite in self.level.sprites:
            if self.brush_copy_for_sprite(sprite) is None:
                issues.append(
                    f"Unknown sprite brush at ({sprite.x}, {sprite.y}): "
                    f"{sprite.name} {sprite.args or ''}".rstrip()
                )
        return issues
