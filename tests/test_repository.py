from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_repository_crud(tmp_path: Path) -> None:
    from nonebot_plugin_game_uid.repository import UIDRepository

    repository = UIDRepository(tmp_path / "nested" / "uid.db")

    assert await repository.get_all("10001") == {}
    assert await repository.set_uid("10001", "genshin", "100123456") is False
    assert await repository.get_uid("10001", "genshin") == "100123456"
    assert await repository.get_all("10001") == {"genshin": "100123456"}

    assert await repository.set_uid("10001", "genshin", "200123456") is True
    assert await repository.get_uid("10001", "genshin") == "200123456"

    assert await repository.delete_uid("10001", "genshin") is True
    assert await repository.delete_uid("10001", "genshin") is False
    assert await repository.get_uid("10001", "genshin") is None


@pytest.mark.asyncio
async def test_repository_separates_users_and_games(tmp_path: Path) -> None:
    from nonebot_plugin_game_uid.repository import UIDRepository

    repository = UIDRepository(tmp_path / "uid.db")
    await repository.set_uid("10001", "genshin", "100123456")
    await repository.set_uid("10001", "starrail", "101234567")
    await repository.set_uid("10002", "genshin", "200123456")

    assert await repository.get_all("10001") == {
        "genshin": "100123456",
        "starrail": "101234567",
    }
    assert await repository.get_all("10002") == {"genshin": "200123456"}
    assert await repository.get_uids_for_users(["10001", "10002", "10003"], "genshin") == {
        "10001": "100123456",
        "10002": "200123456",
    }

    assert await repository.delete_all_uids("10001") == 2
    assert await repository.get_all("10001") == {}
    assert await repository.get_all("10002") == {"genshin": "200123456"}
    assert await repository.delete_all_uids("10001") == 0


@pytest.mark.asyncio
async def test_reminder_crud_and_due_time(tmp_path: Path) -> None:
    from nonebot_plugin_game_uid.repository import UIDRepository

    repository = UIDRepository(tmp_path / "uid.db")
    assert await repository.get_reminder("20001") is None

    await repository.set_reminder("20001", "10000", "genshin", 60, now=1000)
    reminder = await repository.get_reminder("20001")
    assert reminder is not None
    assert reminder.game == "genshin"
    assert reminder.interval_minutes == 60
    assert reminder.next_run_at == 4600
    assert await repository.get_due_reminders(now=4599) == []
    assert await repository.get_due_reminders(now=4600) == [reminder]

    await repository.mark_reminder_sent("20001", now=4600)
    updated = await repository.get_reminder("20001")
    assert updated is not None
    assert updated.next_run_at == 8200
    assert await repository.delete_reminder("20001") is True
    assert await repository.delete_reminder("20001") is False
