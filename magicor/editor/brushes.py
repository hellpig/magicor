"""Brush definitions shared by the Pygame Magicor level editor.

This is a Python 3 adaptation of the original Magicor 1.1 editor brush
module by Peter Gebauer. The original project is dedicated to the public
domain; see the repository LICENSE file.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Optional


class BrushException(Exception):
    """Raised when a brush receives invalid values."""


@dataclass
class Brush:
    width: int
    height: int

    def copy(self) -> "Brush":
        return copy.copy(self)

    @property
    def display_name(self) -> str:
        return self.__class__.__name__.removesuffix("Brush") or "Brush"


class EraseBrush(Brush):
    def __init__(self) -> None:
        super().__init__(32, 32)

    @property
    def display_name(self) -> str:
        return "Erase"


class ResourceBrush(Brush):
    def __init__(self, resource: str, width: int, height: int, offset: int) -> None:
        super().__init__(width, height)
        self.resource = resource
        self.offset = offset

    def update(self, resource: Optional[str]) -> None:
        if resource:
            self.resource = resource


class TileBrush(ResourceBrush):
    def __init__(self, resource: str) -> None:
        super().__init__(resource, 32, 32, 0)

    def __str__(self) -> str:
        return self.resource

    @property
    def display_name(self) -> str:
        return f"Tile: {self.resource.split('/')[-1]}"


class SpriteBrush(ResourceBrush):
    def __init__(
        self,
        name: str,
        resource: str,
        width: int,
        height: int,
        offset: int,
        left: int = 0,
        top: int = 0,
    ) -> None:
        super().__init__(resource, width, height, offset)
        self.name = name
        self.left = left
        self.top = top

    def __str__(self) -> str:
        return self.name

    @property
    def display_name(self) -> str:
        return self.name.replace("-", " ").title()


class PlayerBrush(SpriteBrush):
    def __init__(self, direction: Optional[str] = "right") -> None:
        super().__init__("player", "sprites/player-penguin", 32, 48, 0, 0, -16)
        self.direction = direction

    @property
    def direction(self) -> Optional[str]:
        return self._direction

    @direction.setter
    def direction(self, value: Optional[str]) -> None:
        if value not in (None, "right", "left"):
            raise ValueError(f"invalid direction {value!r}")
        self._direction = value
        self.offset = 4 if value == "left" else 0

    def __str__(self) -> str:
        return f"{self.name} {self.direction}" if self.direction else self.name

    def update(self, args: Optional[str]) -> None:
        self.direction = args or "right"


class FireBrush(SpriteBrush):
    def __init__(self, no_falling: bool | str = False) -> None:
        super().__init__("fire", "sprites/fire-normal", 32, 32, 0)
        self.no_falling = no_falling

    @property
    def no_falling(self) -> bool:
        return self._no_falling

    @no_falling.setter
    def no_falling(self, value: bool | str | None) -> None:
        self._no_falling = value == "nofall" or bool(value)

    def __str__(self) -> str:
        return "fire nofall" if self.no_falling else "fire"

    def update(self, args: Optional[str]) -> None:
        self.no_falling = args


class IceBrush(SpriteBrush):
    CONNECT_VALUES = (None, "connect", "connect-right", "connect-left")

    def __init__(self, connect: Optional[str] = None) -> None:
        super().__init__("ice", "sprites/ice-normal", 32, 32, 4)
        self.connect = connect

    @property
    def connect(self) -> Optional[str]:
        return self._connect

    @connect.setter
    def connect(self, value: Optional[str]) -> None:
        if value == "connect":
            self.offset = 7
            self._connect = value
        elif value == "connect-right":
            self.offset = 6
            self._connect = value
        elif value == "connect-left":
            self.offset = 5
            self._connect = value
        else:
            self.offset = 4
            self._connect = None

    def update(self, args: Optional[str]) -> None:
        self.connect = args

    def __str__(self) -> str:
        return f"ice {self.connect}" if self.connect else "ice"


class LavaBrush(SpriteBrush):
    def __init__(self, dormant: bool | str = False) -> None:
        super().__init__("lava", "sprites/lava", 32, 64, 0)
        self.dormant = dormant

    @property
    def dormant(self) -> bool:
        return self._dormant

    @dormant.setter
    def dormant(self, value: bool | str | None) -> None:
        self._dormant = value == "dormant" or bool(value)
        self.offset = 4 if self._dormant else 0

    def __str__(self) -> str:
        return "lava dormant" if self.dormant else "lava"

    def update(self, args: Optional[str]) -> None:
        self.dormant = args


class TubeBrush(SpriteBrush):
    DIRECTIONS = ("left", "up", "down", "right")

    def __init__(self, direction: str = "left", id_: Optional[str] = None) -> None:
        super().__init__("tube", "sprites/tube-endings", 32, 32, 0)
        self.direction = direction
        self.id = id_

    @property
    def direction(self) -> str:
        return self._direction

    @direction.setter
    def direction(self, value: str) -> None:
        try:
            self.offset = self.DIRECTIONS.index(value)
            self._direction = value
        except ValueError:
            self.offset = 0
            self._direction = "left"

    def update(self, args: Optional[str]) -> None:
        parts = (args or "left").split(" ", 1)
        self.direction = parts[0]
        self.id = parts[1] if len(parts) == 2 and parts[1] else None

    def __str__(self) -> str:
        suffix = f" {self.id}" if self.id else ""
        return f"tube {self.direction}{suffix}"


class EnemyBrush(SpriteBrush):
    def __init__(
        self,
        id_: str,
        name: str,
        resource: str,
        width: int,
        height: int,
        offset: int,
    ) -> None:
        super().__init__(name, resource, width, height, offset)
        self.id = id_


class WalkingEnemyBrush(EnemyBrush):
    DIRECTIONS = ("left", "right")

    def __init__(self, image_resource: str, sound_resource: str, direction: str, speed: int) -> None:
        super().__init__(
            f"walking-enemy {image_resource} {sound_resource}",
            "walking-enemy",
            image_resource,
            32,
            32,
            0,
        )
        self.sound_resource = sound_resource
        self.speed = speed
        self.direction = direction

    @property
    def direction(self) -> str:
        return self._direction

    @direction.setter
    def direction(self, value: str) -> None:
        self._direction = "right" if value == "right" else "left"
        self.offset = 0 if self._direction == "right" else 3

    def update(self, args: Optional[str]) -> None:
        parts = (args or "").split(" ", 3)
        if len(parts) == 4:
            self.direction = parts[0]
            self.speed = int(parts[3])

    def __str__(self) -> str:
        return (
            f"walking-enemy {self.direction} {self.resource} "
            f"{self.sound_resource} {self.speed}"
        )

    @property
    def display_name(self) -> str:
        return f"Walking: {self.resource.split('/')[-1]}"


class ClimbingEnemyBrush(EnemyBrush):
    DIRECTIONS = ("up", "down")

    def __init__(self, image_resource: str, sound_resource: str, direction: str, speed: int) -> None:
        super().__init__(
            f"climbing-enemy {image_resource} {sound_resource}",
            "climbing-enemy",
            image_resource,
            32,
            32,
            0,
        )
        self.sound_resource = sound_resource
        self.speed = speed
        self.direction = direction

    @property
    def direction(self) -> str:
        return self._direction

    @direction.setter
    def direction(self, value: str) -> None:
        self._direction = "up" if value == "up" else "down"
        self.offset = 0 if self._direction == "up" else 3

    def update(self, args: Optional[str]) -> None:
        parts = (args or "").split(" ", 3)
        if len(parts) == 4:
            self.direction = parts[0]
            self.speed = int(parts[3])

    def __str__(self) -> str:
        return (
            f"climbing-enemy {self.direction} {self.resource} "
            f"{self.sound_resource} {self.speed}"
        )

    @property
    def display_name(self) -> str:
        return f"Climbing: {self.resource.split('/')[-1]}"


class StationaryEnemyBrush(EnemyBrush):
    DIRECTIONS = ("up", "left", "down", "right")

    def __init__(self, image_resource: str, sound_resource: str, direction: str, trigger: int) -> None:
        super().__init__(
            f"stationary-enemy {image_resource} {sound_resource}",
            "stationary-enemy",
            image_resource,
            32,
            32,
            0,
        )
        self.sound_resource = sound_resource
        self.trigger = trigger
        self.direction = direction

    @property
    def direction(self) -> str:
        return self._direction

    @direction.setter
    def direction(self, value: str) -> None:
        offsets = {"up": 0, "left": 4, "down": 8, "right": 12}
        self._direction = value if value in offsets else "down"
        self.offset = offsets[self._direction]

    def update(self, args: Optional[str]) -> None:
        parts = (args or "").split(" ", 3)
        if len(parts) == 4:
            self.direction = parts[0]
            self.trigger = int(parts[3])

    def __str__(self) -> str:
        return (
            f"stationary-enemy {self.direction} {self.resource} "
            f"{self.sound_resource} {self.trigger}"
        )

    @property
    def display_name(self) -> str:
        return f"Stationary: {self.resource.split('/')[-1]}"


class DecorationBrush(SpriteBrush):
    def __init__(self, resource: str, width: int, height: int, speed: int) -> None:
        super().__init__("decoration", resource, width, height, 0)
        self.speed = speed

    def update(self, args: Optional[str]) -> None:
        parts = (args or "").split(" ", 3)
        if len(parts) == 4:
            self.speed = int(parts[3])

    def __str__(self) -> str:
        return f"decoration {self.resource} {self.width} {self.height} {self.speed}"

    @property
    def display_name(self) -> str:
        return f"Decor: {self.resource.split('/')[-1]}"


class DirectionBrush(SpriteBrush):
    DIRECTIONS = ("right", "down", "left", "up")

    def __init__(self, direction: str) -> None:
        super().__init__("direction", "sprites/arrow", 32, 32, 0)
        self.direction = direction

    @property
    def direction(self) -> str:
        return self._direction

    @direction.setter
    def direction(self, value: str) -> None:
        self._direction = value if value in self.DIRECTIONS else "right"
        self.offset = self.DIRECTIONS.index(self._direction)

    def update(self, args: Optional[str]) -> None:
        self.direction = args or "right"

    def __str__(self) -> str:
        return f"direction {self.direction}"


class TrapolaBrush(SpriteBrush):
    def __init__(self) -> None:
        super().__init__("trapola", "sprites/trapola2_q", 32, 32, 0)


DEFAULT_BRUSH_FACTORIES = (
    EraseBrush,
    PlayerBrush,
    FireBrush,
    IceBrush,
    lambda: IceBrush("connect"),
    lambda: IceBrush("connect-left"),
    lambda: IceBrush("connect-right"),
    LavaBrush,
    lambda: TubeBrush("left"),
    lambda: TubeBrush("up"),
    lambda: TubeBrush("right"),
    lambda: TubeBrush("down"),
    lambda: DirectionBrush("right"),
    TrapolaBrush,
)
