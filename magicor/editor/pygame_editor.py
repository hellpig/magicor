"""Single-window Pygame frontend for the Magicor level editor.

The editor intentionally follows the feature set of the original PyGTK editor:
level drawing, a data-driven palette, level settings, sprite properties, undo,
grid display, and wraparound scrolling. Standard file chooser dialogs use
Tkinter when it is available; the editor itself is entirely rendered and
controlled through Pygame.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Callable, Optional

import pygame

from magicor.editor.brushes import (
    Brush,
    ClimbingEnemyBrush,
    DecorationBrush,
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
    TubeBrush,
    WalkingEnemyBrush,
)
from magicor.editor.core import EditorDocument, EditorError
from magicor.level import LevelSprite


Color = tuple[int, int, int]

BG: Color = (37, 39, 43)
PANEL: Color = (52, 55, 60)
PANEL_2: Color = (63, 67, 73)
TEXT: Color = (235, 235, 235)
MUTED: Color = (180, 183, 188)
BORDER: Color = (93, 98, 106)
ACCENT: Color = (92, 151, 205)
ACCENT_2: Color = (130, 185, 232)
DANGER: Color = (200, 88, 88)
BLACK: Color = (0, 0, 0)
WHITE: Color = (255, 255, 255)


class FileDialog:
    """Small Tkinter bridge used only for native open/save dialogs."""

    @staticmethod
    def open_level(initial_dir: Path) -> Optional[Path]:
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            value = filedialog.askopenfilename(
                title="Open Magicor level",
                initialdir=str(initial_dir),
                filetypes=(("Magicor levels", "*.lvl"), ("All files", "*.*")),
            )
            root.destroy()
            return Path(value) if value else None
        except Exception:
            return None

    @staticmethod
    def open_resource(initial_dir: Path, title: str, patterns: tuple[tuple[str, str], ...]) -> Optional[Path]:
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            value = filedialog.askopenfilename(
                title=title,
                initialdir=str(initial_dir),
                filetypes=patterns + (("All files", "*.*"),),
            )
            root.destroy()
            return Path(value) if value else None
        except Exception:
            return None

    @staticmethod
    def save_level(initial_dir: Path, initial_name: str = "level.lvl") -> Optional[Path]:
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            value = filedialog.asksaveasfilename(
                title="Save Magicor level",
                initialdir=str(initial_dir),
                initialfile=initial_name,
                defaultextension=".lvl",
                filetypes=(("Magicor levels", "*.lvl"), ("All files", "*.*")),
            )
            root.destroy()
            return Path(value) if value else None
        except Exception:
            return None


class EditorApp:
    BASE_MAP_SIZE = (640, 576)
    MIN_WINDOW = (1050, 690)
    DEFAULT_WINDOW = (1280, 780)

    def __init__(
        self,
        data_path: str | os.PathLike[str] = "data",
        load_file: str | os.PathLike[str] | None = None,
        headless: bool = False,
    ) -> None:
        pygame.init()
        pygame.display.set_caption("Magicor Level Editor")
        flags = pygame.RESIZABLE
        if headless:
            flags |= pygame.HIDDEN
        self.screen = pygame.display.set_mode(self.DEFAULT_WINDOW, flags)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 22)
        self.small_font = pygame.font.Font(None, 18)
        self.heading_font = pygame.font.Font(None, 26)
        self.document = EditorDocument(data_path)
        if load_file:
            self.document.load_level(load_file)
        self.running = True
        self.grid = True
        self.status = "Ready. Left-click paints; right-click edits a sprite."
        self.status_until = 0
        self.selected_brush_index: Optional[int] = 0
        self.selected_sprite: Optional[LevelSprite] = None
        self.sprite_edit_brush: Optional[SpriteBrush] = None
        self.palette_scroll = 0
        self.image_cache: dict[str, Optional[pygame.Surface]] = {}
        self.frame_cache: dict[tuple[str, int, int, int], pygame.Surface] = {}
        self.background_cache_key: Optional[str] = None
        self.background_cache: Optional[pygame.Surface] = None
        self.hover_cell: Optional[tuple[int, int]] = None
        self.map_rect = pygame.Rect(0, 0, *self.BASE_MAP_SIZE)
        self.palette_rect = pygame.Rect(0, 0, 0, 0)
        self.properties_rect = pygame.Rect(0, 0, 0, 0)
        self.toolbar_rect = pygame.Rect(0, 0, 0, 0)
        self.status_rect = pygame.Rect(0, 0, 0, 0)
        self.click_targets: list[tuple[pygame.Rect, Callable[[], None], str]] = []
        self.text_targets: list[tuple[pygame.Rect, str, object, str]] = []
        self.active_text: Optional[tuple[str, object, str]] = None
        self.active_text_original = ""
        self.active_text_value = ""
        self.drawing = False
        self.moving_sprite: Optional[LevelSprite] = None
        self.transaction_started = False
        self.last_draw_cell: Optional[tuple[int, int]] = None
        self.headless = headless
        self._layout()

    # ---------- Layout and generic controls ----------

    @property
    def selected_brush(self) -> Optional[Brush]:
        if self.selected_brush_index is None:
            return None
        if 0 <= self.selected_brush_index < len(self.document.brushes):
            return self.document.brushes[self.selected_brush_index]
        return None

    @property
    def edited_brush(self) -> Optional[Brush]:
        return self.sprite_edit_brush if self.selected_sprite else self.selected_brush

    def _layout(self) -> None:
        width, height = self.screen.get_size()
        toolbar_h = 42
        status_h = 26
        palette_w = 286
        properties_w = 304
        self.toolbar_rect = pygame.Rect(0, 0, width, toolbar_h)
        self.status_rect = pygame.Rect(0, height - status_h, width, status_h)
        self.palette_rect = pygame.Rect(0, toolbar_h, palette_w, height - toolbar_h - status_h)
        self.properties_rect = pygame.Rect(
            width - properties_w,
            toolbar_h,
            properties_w,
            height - toolbar_h - status_h,
        )
        center = pygame.Rect(
            palette_w,
            toolbar_h,
            width - palette_w - properties_w,
            height - toolbar_h - status_h,
        )
        scale = min(
            max(0.1, (center.width - 20) / self.BASE_MAP_SIZE[0]),
            max(0.1, (center.height - 20) / self.BASE_MAP_SIZE[1]),
        )
        map_w = max(1, round(self.BASE_MAP_SIZE[0] * scale))
        map_h = max(1, round(self.BASE_MAP_SIZE[1] * scale))
        self.map_rect = pygame.Rect(0, 0, map_w, map_h)
        self.map_rect.center = center.center

    def set_status(self, text: str, seconds: float = 5.0) -> None:
        self.status = text
        self.status_until = pygame.time.get_ticks() + int(seconds * 1000)

    def _text(self, text: str, color: Color = TEXT, small: bool = False) -> pygame.Surface:
        font = self.small_font if small else self.font
        return font.render(str(text), True, color)

    def _draw_label(self, surface: pygame.Surface, text: str, x: int, y: int, color: Color = TEXT, small: bool = False) -> None:
        surface.blit(self._text(text, color, small), (x, y))

    def _button(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        label: str,
        callback: Callable[[], None],
        *,
        active: bool = False,
        enabled: bool = True,
        danger: bool = False,
        small: bool = False,
    ) -> None:
        mouse = pygame.mouse.get_pos()
        hovered = rect.collidepoint(mouse)
        if not enabled:
            fill = (55, 57, 61)
            fg = (125, 127, 131)
        elif danger:
            fill = DANGER if hovered else (145, 71, 71)
            fg = WHITE
        elif active:
            fill = ACCENT_2 if hovered else ACCENT
            fg = BLACK
        else:
            fill = (87, 91, 98) if hovered else PANEL_2
            fg = TEXT
        pygame.draw.rect(surface, fill, rect, border_radius=3)
        pygame.draw.rect(surface, BORDER, rect, 1, border_radius=3)
        text_surface = self._text(label, fg, small)
        surface.blit(text_surface, text_surface.get_rect(center=rect.center))
        if enabled:
            self.click_targets.append((rect.copy(), callback, label))

    def _checkbox(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        label: str,
        checked: bool,
        callback: Callable[[], None],
    ) -> None:
        box = pygame.Rect(rect.x, rect.y + 1, 18, 18)
        pygame.draw.rect(surface, PANEL_2, box)
        pygame.draw.rect(surface, BORDER, box, 1)
        if checked:
            pygame.draw.line(surface, ACCENT_2, (box.x + 3, box.y + 9), (box.x + 7, box.y + 14), 3)
            pygame.draw.line(surface, ACCENT_2, (box.x + 7, box.y + 14), (box.x + 15, box.y + 4), 3)
        self._draw_label(surface, label, rect.x + 25, rect.y + 1)
        self.click_targets.append((rect.copy(), callback, label))

    def _text_field(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        label: str,
        kind: str,
        target: object,
        attribute: str,
        value: object,
    ) -> None:
        self._draw_label(surface, label, rect.x, rect.y - 18, MUTED, small=True)
        active = self.active_text == (kind, target, attribute)
        shown = self.active_text_value if active else ("" if value is None else str(value))
        pygame.draw.rect(surface, (40, 42, 46), rect)
        pygame.draw.rect(surface, ACCENT if active else BORDER, rect, 2 if active else 1)
        clipped = shown
        while clipped and self.font.size(clipped)[0] > rect.width - 10:
            clipped = clipped[1:]
        self._draw_label(surface, clipped, rect.x + 5, rect.y + 5)
        if active and (pygame.time.get_ticks() // 500) % 2 == 0:
            cursor_x = rect.x + 5 + self.font.size(clipped)[0]
            pygame.draw.line(surface, TEXT, (cursor_x, rect.y + 4), (cursor_x, rect.bottom - 4))
        self.text_targets.append((rect.copy(), kind, target, attribute))

    def _begin_text(self, kind: str, target: object, attribute: str) -> None:
        self._commit_text()
        if kind == "level":
            value = getattr(self.document.level, attribute) or ""
        else:
            value = getattr(target, attribute)
            value = "" if value is None else str(value)
        self.active_text = (kind, target, attribute)
        self.active_text_original = str(value)
        self.active_text_value = str(value)
        pygame.key.start_text_input()

    def _commit_text(self) -> None:
        if not self.active_text:
            return
        kind, target, attribute = self.active_text
        value: object = self.active_text_value
        if kind == "level":
            self.document.set_level_property(attribute, value)
            if attribute == "background":
                self.background_cache_key = None
        elif kind == "brush":
            current = getattr(target, attribute)
            if isinstance(current, int):
                try:
                    value = int(str(value).strip())
                except ValueError:
                    value = current
            elif current is None and attribute == "id":
                value = str(value).strip() or None
            setattr(target, attribute, value)
        self.active_text = None
        pygame.key.stop_text_input()

    def _cancel_text(self) -> None:
        self.active_text = None
        pygame.key.stop_text_input()

    # ---------- Resource rendering ----------

    def _load_image(self, resource: str) -> Optional[pygame.Surface]:
        if resource in self.image_cache:
            return self.image_cache[resource]
        filename = self.document.resolver.find_image(resource)
        if not filename:
            self.image_cache[resource] = None
            return None
        try:
            image = pygame.image.load(str(filename)).convert_alpha()
        except pygame.error:
            image = None
        self.image_cache[resource] = image
        return image

    def _brush_frame(self, brush: Brush) -> pygame.Surface:
        if isinstance(brush, EraseBrush):
            surface = pygame.Surface((32, 32), pygame.SRCALPHA)
            pygame.draw.line(surface, DANGER, (4, 4), (28, 28), 4)
            pygame.draw.line(surface, DANGER, (28, 4), (4, 28), 4)
            return surface
        if not isinstance(brush, ResourceBrush):
            return self._placeholder(32, 32, "?")
        key = (brush.resource, brush.width, brush.height, brush.offset)
        if key in self.frame_cache:
            return self.frame_cache[key]
        source = self._load_image(brush.resource)
        if source is None:
            result = self._placeholder(brush.width, brush.height, "?")
        else:
            x = brush.offset * brush.width
            if x + brush.width <= source.get_width() and brush.height <= source.get_height():
                result = source.subsurface((x, 0, brush.width, brush.height)).copy()
            elif brush.width <= source.get_width() and brush.height <= source.get_height():
                result = source.subsurface((0, 0, brush.width, brush.height)).copy()
            else:
                result = pygame.transform.scale(source, (brush.width, brush.height))
        self.frame_cache[key] = result
        return result

    def _placeholder(self, width: int, height: int, text: str) -> pygame.Surface:
        surface = pygame.Surface((max(1, width), max(1, height)), pygame.SRCALPHA)
        surface.fill((150, 45, 150, 220))
        pygame.draw.rect(surface, WHITE, surface.get_rect(), 1)
        label = self.small_font.render(text, True, WHITE)
        surface.blit(label, label.get_rect(center=surface.get_rect().center))
        return surface

    def _background_surface(self) -> pygame.Surface:
        key = self.document.level.background or ""
        if key == self.background_cache_key and self.background_cache is not None:
            return self.background_cache
        canvas = pygame.Surface(self.BASE_MAP_SIZE)
        canvas.fill(BLACK)
        image = self._load_image(key) if key else None
        if image:
            for y in range(0, canvas.get_height(), image.get_height()):
                for x in range(0, canvas.get_width(), image.get_width()):
                    canvas.blit(image, (x, y))
        self.background_cache_key = key
        self.background_cache = canvas
        return canvas

    def render_level(self) -> pygame.Surface:
        canvas = self._background_surface().copy()
        level = self.document.level
        for y in range(level.height):
            for x in range(level.width):
                resource = level[x, y]
                if not resource or resource == "!":
                    continue
                brush = self.document.brush_by_key.get(f"tile {resource}")
                if isinstance(brush, TileBrush):
                    canvas.blit(self._brush_frame(brush), (x * 32, y * 32))
                else:
                    pygame.draw.rect(canvas, (100, 30, 100), (x * 32, y * 32, 32, 32))
                    self._draw_label(canvas, "?", x * 32 + 10, y * 32 + 7)
        for sprite in level.sprites:
            brush = self.document.brush_copy_for_sprite(sprite)
            if brush is None:
                pygame.draw.rect(canvas, (180, 40, 180), (sprite.x * 32, sprite.y * 32, 32, 32))
                self._draw_label(canvas, "?", sprite.x * 32 + 10, sprite.y * 32 + 7)
                continue
            frame = self._brush_frame(brush)
            canvas.blit(frame, (sprite.x * 32 + brush.left, sprite.y * 32 + brush.top))
        if self.grid:
            for x in range(level.width + 1):
                pygame.draw.line(canvas, (80, 80, 80), (x * 32, 0), (x * 32, 576))
            for y in range(level.height + 1):
                pygame.draw.line(canvas, (80, 80, 80), (0, y * 32), (640, y * 32))
        if self.hover_cell:
            x, y = self.hover_cell
            overlay = pygame.Surface((32, 32), pygame.SRCALPHA)
            overlay.fill((90, 160, 230, 55))
            canvas.blit(overlay, (x * 32, y * 32))
            pygame.draw.rect(canvas, ACCENT_2, (x * 32, y * 32, 32, 32), 2)
        if self.selected_sprite and self.selected_sprite in level.sprites:
            x, y, width, height = self.document.sprite_bounds(self.selected_sprite)
            pygame.draw.rect(canvas, (255, 220, 80), (x * 32, y * 32, width * 32, height * 32), 2)
        return canvas

    # ---------- Drawing panels ----------

    def draw_toolbar(self) -> None:
        pygame.draw.rect(self.screen, PANEL, self.toolbar_rect)
        self.click_targets = []
        self.text_targets = []
        x = 6
        y = 6
        buttons = [
            ("New", self.action_new),
            ("Open", self.action_open),
            ("Save", self.action_save),
            ("Save As", self.action_save_as),
            ("Undo", self.action_undo),
            ("Grid", self.action_grid),
            ("<", lambda: self.action_scroll(-1, 0)),
            (">", lambda: self.action_scroll(1, 0)),
            ("^", lambda: self.action_scroll(0, -1)),
            ("v", lambda: self.action_scroll(0, 1)),
            ("Check", self.action_validate),
        ]
        for label, callback in buttons:
            width = 42 if label in ("<", ">", "^", "v") else max(58, self.font.size(label)[0] + 18)
            rect = pygame.Rect(x, y, width, 29)
            self._button(
                self.screen,
                rect,
                label,
                callback,
                active=(label == "Grid" and self.grid),
                enabled=(label != "Undo" or bool(self.document.undo_stack)),
                small=True,
            )
            x += width + 5

    def draw_palette(self) -> None:
        pygame.draw.rect(self.screen, PANEL, self.palette_rect)
        self._draw_label(self.screen, "Palette", 10, self.palette_rect.y + 8)
        self._draw_label(
            self.screen,
            "Wheel scrolls • click selected sprite to move",
            10,
            self.palette_rect.y + 30,
            MUTED,
            small=True,
        )
        content_top = self.palette_rect.y + 52
        content_rect = pygame.Rect(6, content_top, self.palette_rect.width - 12, self.palette_rect.bottom - content_top - 4)
        old_clip = self.screen.get_clip()
        self.screen.set_clip(content_rect)
        item_h = 54
        columns = 2
        item_w = (content_rect.width - 6) // columns
        total_rows = (len(self.document.brushes) + columns - 1) // columns
        max_scroll = max(0, total_rows * item_h - content_rect.height)
        self.palette_scroll = max(0, min(self.palette_scroll, max_scroll))
        for index, brush in enumerate(self.document.brushes):
            row, col = divmod(index, columns)
            rect = pygame.Rect(
                content_rect.x + col * item_w,
                content_rect.y + row * item_h - self.palette_scroll,
                item_w - 4,
                item_h - 4,
            )
            if rect.bottom < content_rect.top or rect.top > content_rect.bottom:
                continue
            selected = index == self.selected_brush_index and self.selected_sprite is None
            fill = (67, 83, 97) if selected else (58, 61, 66)
            pygame.draw.rect(self.screen, fill, rect, border_radius=3)
            pygame.draw.rect(self.screen, ACCENT if selected else BORDER, rect, 2 if selected else 1, border_radius=3)
            icon = self._brush_frame(brush)
            max_icon = 34
            scale = min(max_icon / max(1, icon.get_width()), max_icon / max(1, icon.get_height()), 1.0)
            if scale != 1.0:
                icon = pygame.transform.scale(icon, (max(1, round(icon.get_width() * scale)), max(1, round(icon.get_height() * scale))))
            icon_rect = icon.get_rect(center=(rect.x + 22, rect.centery))
            self.screen.blit(icon, icon_rect)
            label = brush.display_name
            while label and self.small_font.size(label)[0] > rect.width - 48:
                label = label[:-1]
            if label != brush.display_name and len(label) > 2:
                label = label[:-2] + "…"
            self._draw_label(self.screen, label, rect.x + 43, rect.y + 17, TEXT, small=True)
            self.click_targets.append((rect.copy(), lambda i=index: self.select_brush(i), brush.display_name))
        self.screen.set_clip(old_clip)

    def draw_properties(self) -> None:
        pygame.draw.rect(self.screen, PANEL, self.properties_rect)
        x = self.properties_rect.x + 10
        width = self.properties_rect.width - 20
        y = self.properties_rect.y + 8
        self._draw_label(self.screen, "Level settings", x, y)
        y += 36
        fields = [
            ("Title", "title"),
            ("Credits", "credits"),
            ("Description", "description"),
            ("Hint", "hint"),
            ("Background", "background"),
            ("Music", "music"),
        ]
        for label, attribute in fields:
            has_picker = attribute in ("background", "music")
            field_width = width - 35 if has_picker else width
            rect = pygame.Rect(x, y, field_width, 27)
            self._text_field(
                self.screen,
                rect,
                label,
                "level",
                self.document.level,
                attribute,
                getattr(self.document.level, attribute),
            )
            if has_picker:
                browse = pygame.Rect(rect.right + 5, y, 30, 27)
                callback = self.action_pick_background if attribute == "background" else self.action_pick_music
                self._button(self.screen, browse, "...", callback, small=True)
            y += 49
        check_rect = pygame.Rect(x, y, width, 22)
        self._checkbox(
            self.screen,
            check_rect,
            "Draw shadows",
            bool(self.document.level.shadows),
            lambda: self.document.set_level_property("shadows", not self.document.level.shadows),
        )
        y += 37
        pygame.draw.line(self.screen, BORDER, (x, y), (x + width, y))
        y += 10
        if self.selected_sprite:
            self._draw_label(self.screen, "Selected sprite", x, y)
            y += 25
            self._draw_label(
                self.screen,
                f"Cell: {self.selected_sprite.x}, {self.selected_sprite.y}",
                x,
                y,
                MUTED,
                small=True,
            )
            y += 24
        else:
            self._draw_label(self.screen, "Brush options", x, y)
            y += 28
        y = self._draw_brush_options(x, y, width)
        if self.selected_sprite:
            y += 5
            apply_rect = pygame.Rect(x, y, (width - 6) // 2, 29)
            delete_rect = pygame.Rect(apply_rect.right + 6, y, (width - 6) // 2, 29)
            self._button(self.screen, apply_rect, "Apply", self.apply_sprite_properties, active=True, small=True)
            self._button(self.screen, delete_rect, "Delete", self.delete_selected_sprite, danger=True, small=True)

    def _draw_brush_options(self, x: int, y: int, width: int) -> int:
        brush = self.edited_brush
        if brush is None:
            self._draw_label(self.screen, "No brush selected.", x, y, MUTED, small=True)
            return y + 22
        self._draw_label(self.screen, brush.display_name, x, y, ACCENT_2, small=True)
        y += 25
        if isinstance(brush, PlayerBrush):
            return self._enum_row(x, y, width, "Direction", brush, "direction", ("right", "left"))
        if isinstance(brush, FireBrush):
            rect = pygame.Rect(x, y, width, 22)
            self._checkbox(self.screen, rect, "No falling ice", brush.no_falling, lambda: setattr(brush, "no_falling", not brush.no_falling))
            return y + 30
        if isinstance(brush, IceBrush):
            values = (None, "connect", "connect-right", "connect-left")
            return self._enum_row(x, y, width, "Connection", brush, "connect", values)
        if isinstance(brush, LavaBrush):
            rect = pygame.Rect(x, y, width, 22)
            self._checkbox(self.screen, rect, "Dormant", brush.dormant, lambda: setattr(brush, "dormant", not brush.dormant))
            return y + 30
        if isinstance(brush, TubeBrush):
            y = self._enum_row(x, y, width, "Direction", brush, "direction", TubeBrush.DIRECTIONS)
            rect = pygame.Rect(x, y + 16, width, 27)
            self._text_field(self.screen, rect, "Tube ID", "brush", brush, "id", brush.id)
            return y + 52
        if isinstance(brush, WalkingEnemyBrush):
            y = self._enum_row(x, y, width, "Direction", brush, "direction", WalkingEnemyBrush.DIRECTIONS)
            return self._integer_row(x, y, width, "Speed", brush, "speed", 0, 999)
        if isinstance(brush, ClimbingEnemyBrush):
            y = self._enum_row(x, y, width, "Direction", brush, "direction", ClimbingEnemyBrush.DIRECTIONS)
            return self._integer_row(x, y, width, "Speed", brush, "speed", 0, 999)
        if isinstance(brush, StationaryEnemyBrush):
            y = self._enum_row(x, y, width, "Direction", brush, "direction", StationaryEnemyBrush.DIRECTIONS)
            return self._integer_row(x, y, width, "Trigger", brush, "trigger", 0, 999)
        if isinstance(brush, DecorationBrush):
            return self._integer_row(x, y, width, "Animation speed", brush, "speed", 0, 999)
        if isinstance(brush, DirectionBrush):
            return self._enum_row(x, y, width, "Direction", brush, "direction", DirectionBrush.DIRECTIONS)
        if isinstance(brush, TileBrush):
            self._draw_label(self.screen, brush.resource, x, y, MUTED, small=True)
            return y + 22
        if isinstance(brush, EraseBrush):
            self._draw_label(self.screen, "Removes the tile and overlapping sprites.", x, y, MUTED, small=True)
            return y + 36
        self._draw_label(self.screen, "No editable properties.", x, y, MUTED, small=True)
        return y + 22

    def _enum_row(
        self,
        x: int,
        y: int,
        width: int,
        label: str,
        target: object,
        attribute: str,
        values: tuple[object, ...],
    ) -> int:
        self._draw_label(self.screen, label, x, y, MUTED, small=True)
        y += 18
        current = getattr(target, attribute)
        shown = "none" if current is None else str(current)
        left = pygame.Rect(x, y, 31, 27)
        middle = pygame.Rect(x + 36, y, width - 72, 27)
        right = pygame.Rect(x + width - 31, y, 31, 27)
        self._button(self.screen, left, "<", lambda: self._cycle(target, attribute, values, -1), small=True)
        pygame.draw.rect(self.screen, (40, 42, 46), middle)
        pygame.draw.rect(self.screen, BORDER, middle, 1)
        text = self._text(shown, TEXT, small=True)
        self.screen.blit(text, text.get_rect(center=middle.center))
        self._button(self.screen, right, ">", lambda: self._cycle(target, attribute, values, 1), small=True)
        return y + 36

    def _integer_row(
        self,
        x: int,
        y: int,
        width: int,
        label: str,
        target: object,
        attribute: str,
        minimum: int,
        maximum: int,
    ) -> int:
        self._draw_label(self.screen, label, x, y, MUTED, small=True)
        y += 18
        value = int(getattr(target, attribute))
        left = pygame.Rect(x, y, 31, 27)
        middle = pygame.Rect(x + 36, y, width - 72, 27)
        right = pygame.Rect(x + width - 31, y, 31, 27)
        self._button(
            self.screen,
            left,
            "-",
            lambda: setattr(target, attribute, max(minimum, int(getattr(target, attribute)) - 1)),
            small=True,
        )
        pygame.draw.rect(self.screen, (40, 42, 46), middle)
        pygame.draw.rect(self.screen, BORDER, middle, 1)
        text = self._text(str(value), TEXT, small=True)
        self.screen.blit(text, text.get_rect(center=middle.center))
        self._button(
            self.screen,
            right,
            "+",
            lambda: setattr(target, attribute, min(maximum, int(getattr(target, attribute)) + 1)),
            small=True,
        )
        return y + 36

    @staticmethod
    def _cycle(target: object, attribute: str, values: tuple[object, ...], delta: int) -> None:
        current = getattr(target, attribute)
        try:
            index = values.index(current)
        except ValueError:
            index = 0
        setattr(target, attribute, values[(index + delta) % len(values)])

    def draw_status(self) -> None:
        pygame.draw.rect(self.screen, (30, 31, 34), self.status_rect)
        path = self.document.saved_path.name if self.document.saved_path else "Untitled"
        dirty = " *" if self.document.dirty else ""
        left = f"{path}{dirty}"
        self._draw_label(self.screen, left, 8, self.status_rect.y + 5, MUTED, small=True)
        status_surface = self._text(self.status, MUTED, small=True)
        self.screen.blit(status_surface, (self.status_rect.centerx - status_surface.get_width() // 2, self.status_rect.y + 5))

    def draw(self) -> None:
        self._layout()
        self.screen.fill(BG)
        self.draw_toolbar()
        self.draw_palette()
        self.draw_properties()
        level_surface = self.render_level()
        scaled = pygame.transform.scale(level_surface, self.map_rect.size)
        self.screen.blit(scaled, self.map_rect)
        pygame.draw.rect(self.screen, BORDER, self.map_rect, 2)
        self.draw_status()
        title = "Magicor Level Editor"
        if self.document.saved_path:
            title += f" - {self.document.saved_path.name}"
        if self.document.dirty:
            title += " *"
        pygame.display.set_caption(title)
        pygame.display.flip()

    # ---------- Actions ----------

    def select_brush(self, index: int) -> None:
        self._commit_text()
        self.selected_brush_index = index
        self.selected_sprite = None
        self.sprite_edit_brush = None
        self.set_status(f"Selected {self.document.brushes[index].display_name}.")

    def action_new(self) -> None:
        self._commit_text()
        self.document.new_level()
        self.selected_sprite = None
        self.sprite_edit_brush = None
        self.background_cache_key = None
        self.set_status("Created a new level.")

    def _initial_level_dir(self) -> Path:
        if self.document.saved_path:
            return self.document.saved_path.parent
        levels = self.document.resolver.data_path / "levels"
        return levels if levels.is_dir() else Path.cwd()

    def action_open(self) -> None:
        self._commit_text()
        path = FileDialog.open_level(self._initial_level_dir())
        if path is None:
            self.set_status("Open cancelled, or Tkinter file dialogs are unavailable.")
            return
        try:
            self.document.load_level(path)
            self.selected_sprite = None
            self.sprite_edit_brush = None
            self.background_cache_key = None
            self.set_status(f"Loaded {path}.")
        except EditorError as exc:
            self.set_status(str(exc), 8)

    def action_pick_background(self) -> None:
        self._commit_text()
        path = FileDialog.open_resource(
            self.document.resolver.data_path,
            "Choose level background",
            (("Images", "*.png *.jpg *.jpeg *.gif"),),
        )
        if path is None:
            self.set_status("Background selection cancelled.")
            return
        resource = self._resource_name_from_path(path)
        if resource is None:
            self.set_status("Choose a background inside the data folder.", 8)
            return
        self.document.set_level_property("background", resource)
        self.background_cache_key = None
        self.set_status(f"Background set to {resource}.")

    def action_pick_music(self) -> None:
        self._commit_text()
        path = FileDialog.open_resource(
            self.document.resolver.data_path,
            "Choose level music",
            (("Music", "*.xm *.mod *.ogg *.mp3"),),
        )
        if path is None:
            self.set_status("Music selection cancelled.")
            return
        resource = self._resource_name_from_path(path)
        if resource is None:
            self.set_status("Choose music inside the data folder.", 8)
            return
        self.document.set_level_property("music", resource)
        self.set_status(f"Music set to {resource}.")

    def _resource_name_from_path(self, path: Path) -> Optional[str]:
        path = path.expanduser().resolve()
        roots = (self.document.resolver.data_path, self.document.resolver.data_path / "levels")
        for root in roots:
            try:
                relative = path.relative_to(root)
            except ValueError:
                continue
            parts = list(relative.with_suffix("").parts)
            if parts and parts[-1].startswith("_"):
                parts[-1] = parts[-1][1:]
            return "/".join(parts)
        return None

    def action_save(self) -> None:
        self._commit_text()
        if self.document.saved_path is None:
            self.action_save_as()
            return
        try:
            path = self.document.save_level()
            self.set_status(f"Saved {path}.")
        except EditorError as exc:
            self.set_status(str(exc), 8)

    def action_save_as(self) -> None:
        self._commit_text()
        initial_name = self.document.saved_path.name if self.document.saved_path else "level.lvl"
        path = FileDialog.save_level(self._initial_level_dir(), initial_name)
        if path is None:
            self.set_status("Save cancelled, or Tkinter file dialogs are unavailable.")
            return
        try:
            saved = self.document.save_level(path)
            self.set_status(f"Saved {saved}.")
        except EditorError as exc:
            self.set_status(str(exc), 8)

    def action_undo(self) -> None:
        self._commit_text()
        if self.document.undo():
            self.selected_sprite = None
            self.sprite_edit_brush = None
            self.background_cache_key = None
            self.set_status("Undid the last edit.")
        else:
            self.set_status("Nothing to undo.")

    def action_grid(self) -> None:
        self.grid = not self.grid
        self.set_status(f"Grid {'enabled' if self.grid else 'disabled'}.")

    def action_scroll(self, dx: int, dy: int) -> None:
        self._commit_text()
        self.document.scroll(dx, dy)
        self.selected_sprite = None
        self.sprite_edit_brush = None
        direction = {(1, 0): "right", (-1, 0): "left", (0, 1): "down", (0, -1): "up"}[(dx, dy)]
        self.set_status(f"Wrapped the level one cell {direction}.")

    def action_validate(self) -> None:
        issues = self.document.validate()
        if issues:
            self.set_status("; ".join(issues[:3]), 10)
        else:
            self.set_status("No basic level-structure problems found.")

    def apply_sprite_properties(self) -> None:
        self._commit_text()
        if not self.selected_sprite or not self.sprite_edit_brush:
            return
        if self.selected_sprite not in self.document.level.sprites:
            self.selected_sprite = None
            self.sprite_edit_brush = None
            return
        self.document.change()
        self.document.update_sprite(self.selected_sprite, self.sprite_edit_brush)
        self.set_status("Updated sprite properties.")

    def delete_selected_sprite(self) -> None:
        self._commit_text()
        if self.selected_sprite and self.selected_sprite in self.document.level.sprites:
            self.document.change()
            self.document.level.sprites.remove(self.selected_sprite)
            self.set_status("Deleted selected sprite.")
        self.selected_sprite = None
        self.sprite_edit_brush = None

    # ---------- Map interaction ----------

    def screen_to_cell(self, pos: tuple[int, int]) -> Optional[tuple[int, int]]:
        if not self.map_rect.collidepoint(pos):
            return None
        px = (pos[0] - self.map_rect.x) * self.BASE_MAP_SIZE[0] / self.map_rect.width
        py = (pos[1] - self.map_rect.y) * self.BASE_MAP_SIZE[1] / self.map_rect.height
        x, y = int(px // 32), int(py // 32)
        if 0 <= x < 20 and 0 <= y < 18:
            return x, y
        return None

    def _start_transaction(self) -> None:
        if not self.transaction_started:
            self.document.change()
            self.transaction_started = True

    def _paint_cell(self, cell: tuple[int, int]) -> None:
        if cell == self.last_draw_cell:
            return
        brush = self.selected_brush
        if brush is None:
            return
        self._start_transaction()
        self.document.apply_brush(cell[0], cell[1], brush)
        self.last_draw_cell = cell

    def map_mouse_down(self, event: pygame.event.Event) -> None:
        cell = self.screen_to_cell(event.pos)
        if cell is None:
            return
        self._commit_text()
        x, y = cell
        if event.button == 3:
            sprite = self.document.sprite_at(x, y)
            self.selected_sprite = sprite
            self.sprite_edit_brush = self.document.brush_copy_for_sprite(sprite) if sprite else None
            if sprite:
                self.set_status(f"Editing {sprite.name} at ({sprite.x}, {sprite.y}).")
            else:
                self.set_status("No sprite at that cell.")
            return
        if event.button != 1:
            return
        sprite = self.document.sprite_at(x, y)
        brush = self.selected_brush
        should_move = sprite is not None and (
            brush is None
            or (isinstance(brush, SpriteBrush) and brush.name == sprite.name)
            or bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)
        )
        self.transaction_started = False
        self.last_draw_cell = None
        if should_move:
            self._start_transaction()
            self.moving_sprite = sprite
            self.selected_sprite = sprite
            self.sprite_edit_brush = self.document.brush_copy_for_sprite(sprite)
            self.drawing = False
        else:
            self.drawing = True
            self.moving_sprite = None
            self.selected_sprite = None
            self.sprite_edit_brush = None
            self._paint_cell(cell)

    def map_mouse_motion(self, event: pygame.event.Event) -> None:
        cell = self.screen_to_cell(event.pos)
        self.hover_cell = cell
        if cell is None:
            return
        if self.drawing:
            self._paint_cell(cell)
        elif self.moving_sprite:
            self.document.move_sprite(self.moving_sprite, *cell)

    def map_mouse_up(self) -> None:
        self.drawing = False
        self.moving_sprite = None
        self.transaction_started = False
        self.last_draw_cell = None

    # ---------- Events ----------

    def handle_keydown(self, event: pygame.event.Event) -> None:
        if self.active_text:
            if event.key == pygame.K_RETURN:
                self._commit_text()
            elif event.key == pygame.K_ESCAPE:
                self._cancel_text()
            elif event.key == pygame.K_BACKSPACE:
                self.active_text_value = self.active_text_value[:-1]
            elif event.key == pygame.K_DELETE:
                self.active_text_value = ""
            return
        mods = pygame.key.get_mods()
        ctrl = bool(mods & pygame.KMOD_CTRL)
        shift = bool(mods & pygame.KMOD_SHIFT)
        alt = bool(mods & pygame.KMOD_ALT)
        if ctrl and event.key == pygame.K_n:
            self.action_new()
        elif ctrl and event.key == pygame.K_o:
            self.action_open()
        elif ctrl and event.key == pygame.K_s and shift:
            self.action_save_as()
        elif ctrl and event.key == pygame.K_s:
            self.action_save()
        elif ctrl and event.key == pygame.K_z:
            self.action_undo()
        elif ctrl and event.key == pygame.K_g:
            self.action_grid()
        elif alt and event.key == pygame.K_LEFT:
            self.action_scroll(-1, 0)
        elif alt and event.key == pygame.K_RIGHT:
            self.action_scroll(1, 0)
        elif alt and event.key == pygame.K_UP:
            self.action_scroll(0, -1)
        elif alt and event.key == pygame.K_DOWN:
            self.action_scroll(0, 1)
        elif event.key == pygame.K_DELETE:
            self.delete_selected_sprite()
        elif event.key == pygame.K_ESCAPE:
            self.selected_sprite = None
            self.sprite_edit_brush = None
        elif event.key == pygame.K_F5:
            self.action_validate()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._commit_text()
            self.running = False
        elif event.type == pygame.VIDEORESIZE:
            width = max(self.MIN_WINDOW[0], event.w)
            height = max(self.MIN_WINDOW[1], event.h)
            self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
            self._layout()
        elif event.type == pygame.TEXTINPUT and self.active_text:
            self.active_text_value += event.text
        elif event.type == pygame.KEYDOWN:
            self.handle_keydown(event)
        elif event.type == pygame.MOUSEWHEEL:
            mouse = pygame.mouse.get_pos()
            if self.palette_rect.collidepoint(mouse):
                self.palette_scroll -= event.y * 60
        elif event.type == pygame.MOUSEMOTION:
            self.map_mouse_motion(event)
        elif event.type == pygame.MOUSEBUTTONUP:
            self.map_mouse_up()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button in (4, 5) and self.palette_rect.collidepoint(event.pos):
                self.palette_scroll += -60 if event.button == 4 else 60
                return
            # Text fields get first priority.
            for rect, kind, target, attribute in reversed(self.text_targets):
                if rect.collidepoint(event.pos):
                    self._begin_text(kind, target, attribute)
                    return
            # Then normal controls.
            for rect, callback, _label in reversed(self.click_targets):
                if rect.collidepoint(event.pos):
                    self._commit_text()
                    callback()
                    return
            if self.map_rect.collidepoint(event.pos):
                self.map_mouse_down(event)
            else:
                self._commit_text()

    def run(self, max_frames: Optional[int] = None) -> None:
        frames = 0
        while self.running:
            for event in pygame.event.get():
                self.handle_event(event)
            self.draw()
            self.clock.tick(60)
            frames += 1
            if max_frames is not None and frames >= max_frames:
                break
        pygame.quit()


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Edit Magicor .lvl files using Pygame.")
    parser.add_argument("level", nargs="?", help="Level file to open at startup")
    parser.add_argument(
        "--data-path",
        default="data",
        help="Path to the Magicor data folder (default: data)",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_argument_parser().parse_args(argv)
    try:
        app = EditorApp(args.data_path, args.level)
    except (EditorError, pygame.error) as exc:
        print(f"Magicor Level Editor could not start: {exc}", file=sys.stderr)
        return 1
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
