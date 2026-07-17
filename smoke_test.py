"""Automated smoke tests for the Python 3 / Pygame 2 Magicor port."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

if not (ROOT / "data").is_dir():
    raise SystemExit("Extract the original Magicor data folder beside Magicor.py first.")

import pygame

from magicor import ConfigDict, GameEngine, set_group
from magicor.level import Level
from magicor.sprites import AnimationGroup
from magicor.sprites.blocks import BlocksGroup, NormalIce
from magicor.sprites.player import Player
from magicor.sprites.world import Tube
from magicor.states import ErrorState
from magicor.states.play import PlayState
from magicor.states.title import LevelSelectState


def make_config(*, eyecandy: bool = False) -> ConfigDict:
    return ConfigDict(
        {
            "data_path": "data",
            "user_path": str(ROOT / ".test-user"),
            "sound": 0,
            "music": 0,
            "joystick": 0,
            "eyecandy": int(eyecandy),
            "fullscreen": 0,
            "default_tile": "tiles/stone",
            "sound_vol": 100,
            "music_vol": 100,
        }
    )


def make_groups():
    blocks = BlocksGroup()
    fires = AnimationGroup()
    world = AnimationGroup()
    lights = AnimationGroup()
    enemies = AnimationGroup()
    players = AnimationGroup()
    for name, group in {
        "blocks": blocks,
        "fires": fires,
        "world": world,
        "lights": lights,
        "enemies": enemies,
        "players": players,
        "stones": AnimationGroup(),
    }.items():
        set_group(name, group)
    return blocks, fires, world, lights, enemies, players


def make_floor_level() -> Level:
    level = Level()
    for x in range(level.width):
        level[x, 2] = "tiles/stone"
    return level


def test_levels() -> int:
    config = make_config(eyecandy=True)
    engine = GameEngine(config)
    selection = LevelSelectState(config, None, engine.screen)
    actions = ("keyRight", "keyLeft", "keyAction", "keyDown", "keyUp")
    failures = []
    for index, level in enumerate(selection.levels):
        selection.resources.clearLevelResources()
        selection.resources.addLevelResources(selection.levelPaths[level])
        state = PlayState(config, selection.data, engine.screen, level, LevelSelectState)
        if isinstance(next(state), ErrorState):
            failures.append((level.title, "initialization entered ErrorState"))
            continue
        try:
            for frame in range(120):
                state.controls.clear()
                if frame >= 20 and frame % 12 == 0:
                    setattr(state.controls, actions[(frame // 12) % len(actions)], True)
                state.run()
                nxt = next(state)
                if isinstance(nxt, ErrorState):
                    raise RuntimeError("entered ErrorState")
                if isinstance(nxt, PlayState) and nxt is not state:
                    state = nxt
        except Exception as exc:  # report every level before failing
            failures.append((level.title, f"{type(exc).__name__}: {exc}"))
    if failures:
        raise AssertionError(f"Level failures: {failures}")
    return len(selection.levels)


def test_collision_compatibility(engine: GameEngine) -> None:
    for prefix in ("tiles", "sprites", "samples", "fonts"):
        engine.resources.addResources(prefix)

    probe_group = AnimationGroup()
    dummy = pygame.sprite.Sprite()
    dummy.rect = pygame.Rect(64, 32, 32, 32)
    probe_group.add(dummy)
    assert probe_group.getSprite(64, 32, 0, 32) is dummy
    assert probe_group.getSprite(64, 32, 32, 0) is dummy

    level = make_floor_level()
    blocks, fires, world, lights, enemies, players = make_groups()
    player = Player(32, 32, level, players, blocks, fires, world, lights, enemies, False)
    players.add(player)
    ice = NormalIce(64, 32, level, blocks, lights, players, enemies, False)
    ice.created = True
    player.moving = 8
    player.physics()
    assert player.pushing and ice.moving > 0

    level = make_floor_level()
    blocks, fires, world, lights, enemies, players = make_groups()
    entry = Tube(64, 32, level, "left", "pair", blocks, world, players)
    exit_tube = Tube(160, 32, level, "right", "pair", blocks, world, players)
    world.add(entry, exit_tube)
    level[2, 1] = "!"
    level[5, 1] = "!"
    player = Player(32, 32, level, players, blocks, fires, world, lights, enemies, False)
    players.add(player)
    player.moving = 8
    player.physics()
    assert player.tubed and player._animationName == "tube-right"

    level = make_floor_level()
    blocks, fires, world, lights, enemies, players = make_groups()
    entry = Tube(32, 64, level, "up", "vertical", blocks, world, players)
    exit_tube = Tube(128, 32, level, "down", "vertical", blocks, world, players)
    world.add(entry, exit_tube)
    level[1, 2] = "!"
    level[4, 1] = "!"
    level[4, 2] = None
    player = Player(32, 32, level, players, blocks, fires, world, lights, enemies, False)
    players.add(player)
    player.goDown()
    assert player.tubed and player.vertical == 8


def test_audio_assets() -> tuple[int, int]:
    if not pygame.mixer.get_init():
        pygame.mixer.init(44100, -16, 2, 4096)
    wavs = sorted((ROOT / "data").rglob("*.wav"))
    music_files = sorted(
        path
        for path in (ROOT / "data").rglob("*")
        if path.suffix.lower() in {".xm", ".mod", ".ogg", ".mp3"}
    )
    for path in wavs:
        pygame.mixer.Sound(str(path))
    for path in music_files:
        pygame.mixer.music.load(str(path))
    return len(wavs), len(music_files)


def main() -> None:
    level_count = test_levels()
    config = make_config()
    engine = GameEngine(config)
    test_collision_compatibility(engine)
    wav_count, music_count = test_audio_assets()
    pygame.quit()
    print(f"PASS: {level_count} levels, collision probes, ice/tubes, "
          f"{wav_count} sounds, {music_count} music files")


if __name__ == "__main__":
    main()
