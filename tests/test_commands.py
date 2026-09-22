def test_get_mentioned_user() -> None:
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from nonebot_plugin_game_uid.commands import get_mentioned_user

    message = Message([MessageSegment.text("原神 "), MessageSegment.at("123456")])
    assert get_mentioned_user(message) == "123456"


def test_get_mentioned_user_ignores_all() -> None:
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from nonebot_plugin_game_uid.commands import get_mentioned_user

    assert get_mentioned_user(Message(MessageSegment.at("all"))) is None


def test_parse_game_argument() -> None:
    from nonebot_plugin_game_uid.commands import parse_game_argument

    game, error = parse_game_argument("星铁")
    assert error is None
    assert game is not None
    assert game.key == "starrail"


def test_parse_empty_game_argument() -> None:
    from nonebot_plugin_game_uid.commands import parse_game_argument

    game, error = parse_game_argument("")
    assert game is None
    assert error is None


def test_format_bindings() -> None:
    from nonebot_plugin_game_uid.commands import format_bindings
    from nonebot_plugin_game_uid.games import resolve_game

    assert format_bindings({"genshin": "100123456", "zzz": "100987654"}) == (
        "原神：100123456\n绝区零：100987654"
    )
    assert format_bindings({}, resolve_game("原神")) == "尚未绑定原神 UID。"


def test_format_group_uid_list_prefers_group_card() -> None:
    from nonebot_plugin_game_uid.commands import format_group_uid_list
    from nonebot_plugin_game_uid.games import resolve_game

    game = resolve_game("原神")
    assert game is not None
    members = [
        {"user_id": 10001, "card": "群名片A", "nickname": "昵称A"},
        {"user_id": 10002, "card": "", "nickname": "昵称B"},
        {"user_id": 10003, "card": "未绑定", "nickname": "未绑定"},
    ]
    assert format_group_uid_list(
        game,
        members,
        {"10001": "100123456", "10002": "100654321"},
        limit=100,
    ) == "本群原神 UID 列表（2人）：\n群名片A：100123456\n昵称B：100654321"


def test_format_group_uid_list_empty() -> None:
    from nonebot_plugin_game_uid.commands import format_group_uid_list
    from nonebot_plugin_game_uid.games import resolve_game

    game = resolve_game("星布谷地")
    assert game is not None
    assert format_group_uid_list(game, [], {}, limit=100) == "本群还没有群友绑定星布谷地 UID。"
