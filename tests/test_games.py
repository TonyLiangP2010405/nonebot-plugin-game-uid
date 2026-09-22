import pytest


@pytest.mark.parametrize(
    ("alias", "key"),
    [
        ("星布谷地", "starry"),
        ("星布谷底", "starry"),
        ("原神", "genshin"),
        ("星铁", "starrail"),
        ("铁道", "starrail"),
        ("HSR", "starrail"),
        ("绝区零", "zzz"),
        ("ZZZ", "zzz"),
    ],
)
def test_resolve_game(alias: str, key: str) -> None:
    from nonebot_plugin_game_uid.games import resolve_game

    game = resolve_game(alias)
    assert game is not None
    assert game.key == key


@pytest.mark.parametrize("uid", ["12345", "100123456", "0" * 20])
def test_validate_uid_accepts_numeric_values(uid: str) -> None:
    from nonebot_plugin_game_uid.games import validate_uid

    assert validate_uid(uid) == uid


@pytest.mark.parametrize("uid", ["1234", "0" * 21, "12a45", "１２３４５", ""])
def test_validate_uid_rejects_invalid_values(uid: str) -> None:
    from nonebot_plugin_game_uid.games import validate_uid

    assert validate_uid(uid) is None
