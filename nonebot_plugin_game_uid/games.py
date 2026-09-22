from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Game:
    key: str
    name: str
    aliases: tuple[str, ...]


GAMES: tuple[Game, ...] = (
    Game("starry", "星布谷地", ("星布谷地", "星布谷底", "星布", "谷地", "谷底")),
    Game("genshin", "原神", ("原神", "ys")),
    Game(
        "starrail",
        "崩坏：星穹铁道",
        ("崩坏：星穹铁道", "崩坏星穹铁道", "星穹铁道", "星铁", "铁道", "崩铁", "hsr"),
    ),
    Game("zzz", "绝区零", ("绝区零", "绝区", "zzz")),
)

GAME_BY_KEY = {game.key: game for game in GAMES}
GAME_BY_ALIAS = {alias.casefold(): game for game in GAMES for alias in game.aliases}


def resolve_game(value: str) -> Game | None:
    """将游戏名或别名规范化为受支持的游戏。"""

    return GAME_BY_ALIAS.get(value.strip().casefold())


def validate_uid(value: str) -> str | None:
    """验证 UID，成功时返回清理后的 UID。"""

    uid = value.strip()
    if not uid.isascii() or not uid.isdecimal() or not 5 <= len(uid) <= 20:
        return None
    return uid
