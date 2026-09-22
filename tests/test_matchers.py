from pathlib import Path

import pytest
from nonebug import App


def make_group_event(message, *, role="member", user_id=10001):
    from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
    from nonebot.adapters.onebot.v11.event import Sender

    return GroupMessageEvent(
        time=0,
        self_id=10000,
        post_type="message",
        message_type="group",
        sub_type="normal",
        message_id=1,
        user_id=user_id,
        group_id=20001,
        message=Message(message),
        original_message=Message(message),
        raw_message=str(message),
        font=0,
        sender=Sender(user_id=user_id, nickname="测试群友", role=role),
    )


def make_private_event(message):
    from nonebot.adapters.onebot.v11 import Message, PrivateMessageEvent
    from nonebot.adapters.onebot.v11.event import Sender

    return PrivateMessageEvent(
        time=0,
        self_id=10000,
        post_type="message",
        message_type="private",
        sub_type="friend",
        message_id=1,
        user_id=10001,
        message=Message(message),
        original_message=Message(message),
        raw_message=str(message),
        font=0,
        sender=Sender(user_id=10001, nickname="测试用户"),
    )


@pytest.fixture
def repository(tmp_path: Path, monkeypatch):
    from nonebot_plugin_game_uid import commands
    from nonebot_plugin_game_uid.repository import UIDRepository

    instance = UIDRepository(tmp_path / "uid.db")
    monkeypatch.setattr(commands, "get_repository", lambda: instance)
    return instance


async def test_bind_uid(app: App, repository) -> None:
    from nonebot.adapters.onebot.v11 import Bot

    from nonebot_plugin_game_uid.commands import uid_bind

    async with app.test_matcher(uid_bind) as ctx:
        bot = ctx.create_bot(base=Bot, self_id="10000")
        event = make_group_event("/绑定UID 原神 100123456")
        ctx.receive_event(bot, event)
        ctx.should_pass_rule(uid_bind)
        ctx.should_call_send(event, "已绑定原神 UID：100123456", result=None, bot=bot)
        ctx.should_finished(uid_bind)

    assert await repository.get_uid("10001", "genshin") == "100123456"


async def test_bind_uid_rejects_empty_argument(app: App, repository) -> None:
    from nonebot.adapters.onebot.v11 import Bot

    from nonebot_plugin_game_uid.commands import BIND_USAGE, uid_bind

    async with app.test_matcher(uid_bind) as ctx:
        bot = ctx.create_bot(base=Bot, self_id="10000")
        event = make_group_event("/绑定UID")
        ctx.receive_event(bot, event)
        ctx.should_pass_rule(uid_bind)
        ctx.should_call_send(event, BIND_USAGE, result=None, bot=bot)
        ctx.should_finished(uid_bind)

    assert await repository.get_all("10001") == {}


async def test_bind_uid_rejects_invalid_uid(app: App, repository) -> None:
    from nonebot.adapters.onebot.v11 import Bot

    from nonebot_plugin_game_uid.commands import uid_bind

    async with app.test_matcher(uid_bind) as ctx:
        bot = ctx.create_bot(base=Bot, self_id="10000")
        event = make_group_event("/绑定UID 星布谷地 abc")
        ctx.receive_event(bot, event)
        ctx.should_pass_rule(uid_bind)
        ctx.should_call_send(event, "UID 必须是 5～20 位半角数字。", result=None, bot=bot)
        ctx.should_finished(uid_bind)

    assert await repository.get_all("10001") == {}


async def test_private_query_uid(app: App, repository) -> None:
    from nonebot.adapters.onebot.v11 import Bot

    from nonebot_plugin_game_uid.commands import uid_query

    await repository.set_uid("10001", "starrail", "101234567")
    async with app.test_matcher(uid_query) as ctx:
        bot = ctx.create_bot(base=Bot, self_id="10000")
        event = make_private_event("/游戏UID 星铁")
        ctx.receive_event(bot, event)
        ctx.should_pass_rule(uid_query)
        ctx.should_call_send(
            event,
            "你的 UID：\n崩坏：星穹铁道：101234567",
            result=None,
            bot=bot,
        )
        ctx.should_finished(uid_query)


async def test_delete_uid(app: App, repository) -> None:
    from nonebot.adapters.onebot.v11 import Bot

    from nonebot_plugin_game_uid.commands import uid_delete

    await repository.set_uid("10001", "zzz", "100987654")
    async with app.test_matcher(uid_delete) as ctx:
        bot = ctx.create_bot(base=Bot, self_id="10000")
        event = make_group_event("/删除UID 绝区零")
        ctx.receive_event(bot, event)
        ctx.should_pass_rule(uid_delete)
        ctx.should_call_send(event, "已删除绝区零 UID。", result=None, bot=bot)
        ctx.should_finished(uid_delete)

    assert await repository.get_uid("10001", "zzz") is None


async def test_clear_one_uid(app: App, repository) -> None:
    from nonebot.adapters.onebot.v11 import Bot

    from nonebot_plugin_game_uid.commands import uid_clear

    await repository.set_uid("10001", "genshin", "100123456")
    await repository.set_uid("10001", "starrail", "101234567")
    async with app.test_matcher(uid_clear) as ctx:
        bot = ctx.create_bot(base=Bot, self_id="10000")
        event = make_group_event("/清空UID 原神")
        ctx.receive_event(bot, event)
        ctx.should_pass_rule(uid_clear)
        ctx.should_call_send(event, "已清空你的原神 UID。", result=None, bot=bot)
        ctx.should_finished(uid_clear)

    assert await repository.get_all("10001") == {"starrail": "101234567"}


async def test_clear_all_uids_only_affects_current_user(app: App, repository) -> None:
    from nonebot.adapters.onebot.v11 import Bot

    from nonebot_plugin_game_uid.commands import uid_clear

    await repository.set_uid("10001", "genshin", "100123456")
    await repository.set_uid("10001", "zzz", "100987654")
    await repository.set_uid("10002", "genshin", "200123456")
    async with app.test_matcher(uid_clear) as ctx:
        bot = ctx.create_bot(base=Bot, self_id="10000")
        event = make_group_event("/清空UID")
        ctx.receive_event(bot, event)
        ctx.should_pass_rule(uid_clear)
        ctx.should_call_send(event, "已一键清空你的全部游戏 UID（共 2 项）。", result=None, bot=bot)
        ctx.should_finished(uid_clear)

    assert await repository.get_all("10001") == {}
    assert await repository.get_all("10002") == {"genshin": "200123456"}


async def test_bind_help(app: App) -> None:
    from nonebot.adapters.onebot.v11 import Bot

    from nonebot_plugin_game_uid.commands import BIND_HELP_TEXT, bind_help

    async with app.test_matcher(bind_help) as ctx:
        bot = ctx.create_bot(base=Bot, self_id="10000")
        event = make_group_event("/绑定帮助")
        ctx.receive_event(bot, event)
        ctx.should_pass_rule(bind_help)
        ctx.should_call_send(event, BIND_HELP_TEXT, result=None, bot=bot)
        ctx.should_finished(bind_help)


async def test_group_uid_list_uses_group_cards(app: App, repository, monkeypatch) -> None:
    from unittest.mock import AsyncMock

    from nonebot.adapters.onebot.v11 import Bot

    from nonebot_plugin_game_uid.commands import group_uid_list

    members = [
        {"user_id": 10001, "card": "旅行者", "nickname": "昵称一"},
        {"user_id": 10002, "card": "开拓者", "nickname": "昵称二"},
    ]
    monkeypatch.setattr(Bot, "get_group_member_list", AsyncMock(return_value=members), raising=False)
    await repository.set_uid("10001", "genshin", "100123456")
    await repository.set_uid("10002", "genshin", "100654321")

    async with app.test_matcher(group_uid_list) as ctx:
        bot = ctx.create_bot(base=Bot, self_id="10000")
        event = make_group_event("/群UID 原神")
        ctx.receive_event(bot, event)
        ctx.should_pass_rule(group_uid_list)
        ctx.should_call_send(
            event,
            "本群原神 UID 列表（2人）：\n旅行者：100123456\n开拓者：100654321",
            result=None,
            bot=bot,
        )
        ctx.should_finished(group_uid_list)


async def test_set_reminder_as_superuser(app: App, repository) -> None:
    from nonebot.adapters.onebot.v11 import Bot

    from nonebot_plugin_game_uid.commands import reminder_set

    async with app.test_matcher(reminder_set) as ctx:
        bot = ctx.create_bot(base=Bot, self_id="10000")
        event = make_group_event("/设置UID提醒 6小时 原神")
        ctx.receive_event(bot, event)
        ctx.should_pass_permission(reminder_set)
        ctx.should_call_send(
            event,
            "已设置原神 UID 定时提醒，每 6小时发送一次。\n"
            "提醒内容：\n"
            "想查看本群群友的原神 UID 并添加游戏好友？\n"
            "发送 /群UID 原神，即可查看群友主动绑定的 UID（群名片：UID）。\n\n"
            "全部命令：\n"
            "/绑定UID <游戏> <UID> — 绑定或更新自己的 UID\n"
            "/游戏UID [游戏] [@群友] — 查询自己或群友的 UID\n"
            "/删除UID <游戏> — 删除自己的指定游戏 UID\n"
            "/清空UID [游戏] — 清空自己的指定游戏或全部 UID\n"
            "/绑定帮助 — 查看 UID 绑定说明和示例\n"
            "/群UID <游戏> — 查看本群“群名片：UID”列表\n"
            "/设置UID提醒 <间隔> <游戏> — SUPERUSER 开启或更新定时提醒\n"
            "/关闭UID提醒 — SUPERUSER 关闭定时提醒\n"
            "/UID提醒状态 — 查看本群提醒设置\n"
            "/UID帮助 — 查看完整帮助",
            result=None,
            bot=bot,
        )
        ctx.should_finished(reminder_set)

    reminder = await repository.get_reminder("20001")
    assert reminder is not None
    assert reminder.game == "genshin"
    assert reminder.interval_minutes == 360


async def test_set_reminder_rejects_non_superuser_admin(app: App, repository) -> None:
    from nonebot.adapters.onebot.v11 import Bot

    from nonebot_plugin_game_uid.commands import reminder_set

    async with app.test_matcher(reminder_set) as ctx:
        bot = ctx.create_bot(base=Bot, self_id="10000")
        event = make_group_event("/设置UID提醒 6小时 原神", role="admin", user_id=10002)
        ctx.receive_event(bot, event)
        ctx.should_not_pass_permission(reminder_set)
    assert await repository.get_reminder("20001") is None
