from pathlib import Path
from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def repository(tmp_path: Path, monkeypatch):
    from nonebot_plugin_game_uid import commands
    from nonebot_plugin_game_uid.repository import UIDRepository

    instance = UIDRepository(tmp_path / "uid.db")
    monkeypatch.setattr(commands, "get_repository", lambda: instance)
    return instance


@pytest.mark.parametrize(
    ("value", "minutes"),
    [("10分钟", 10), ("30分", 30), ("6小时", 360), ("2时", 120), ("1天", 1440)],
)
def test_parse_duration(value: str, minutes: int) -> None:
    from nonebot_plugin_game_uid.reminders import parse_duration

    assert parse_duration(value) == minutes


@pytest.mark.parametrize("value", ["9分钟", "31天", "6", "六小时", "0天", ""])
def test_parse_duration_rejects_invalid_value(value: str) -> None:
    from nonebot_plugin_game_uid.reminders import parse_duration

    assert parse_duration(value) is None


def test_build_reminder_message_contains_list_command() -> None:
    from nonebot_plugin_game_uid.reminders import build_reminder_message

    assert build_reminder_message("genshin") == (
        "想查看本群群友的原神 UID 并添加游戏好友？\n"
        "发送 /群UID 原神，即可查看群友主动绑定的 UID（群名片：UID）。"
    )


async def test_dispatch_due_reminders(repository, monkeypatch) -> None:
    from nonebot_plugin_game_uid import reminders

    bot = AsyncMock()
    await repository.set_reminder("20001", "10000", "starry", 10, now=1000)
    monkeypatch.setattr(reminders, "get_bots", lambda: {"10000": bot})

    assert await reminders.dispatch_due_reminders(now=1599) == 0
    assert await reminders.dispatch_due_reminders(now=1600) == 1
    bot.call_api.assert_awaited_once_with(
        "send_group_msg",
        group_id=20001,
        message=(
            "想查看本群群友的星布谷地 UID 并添加游戏好友？\n"
            "发送 /群UID 星布谷地，即可查看群友主动绑定的 UID（群名片：UID）。"
        ),
    )
    assert await reminders.dispatch_due_reminders(now=1601) == 0
