from __future__ import annotations

from pathlib import Path

import nonebot_plugin_localstore as localstore
from nonebot import get_plugin_config, logger, on_command
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageEvent, MessageSegment
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER

from .config import Config
from .games import GAME_BY_KEY, GAMES, Game, resolve_game, validate_uid
from .reminders import build_reminder_message, format_duration, parse_duration
from .repository import UIDRepository

BIND_USAGE = "用法：/绑定UID <游戏> <UID>\n例如：/绑定UID 原神 100123456"
QUERY_USAGE = "用法：/游戏UID [游戏] [@群友]\n例如：/游戏UID 星铁 @某位群友"
DELETE_USAGE = "用法：/删除UID <游戏>\n例如：/删除UID 绝区零"
GROUP_LIST_USAGE = "用法：/群UID <游戏>\n例如：/群UID 星布谷地"
REMINDER_USAGE = "用法：/设置UID提醒 <间隔> <游戏>\n例如：/设置UID提醒 6小时 原神\n间隔范围：10分钟～30天"

uid_bind = on_command(
    "绑定UID",
    aliases={"绑定uid", "绑定游戏UID", "绑定游戏uid"},
    priority=10,
    block=True,
)
uid_query = on_command(
    "游戏UID",
    aliases={"游戏uid", "UID", "uid", "我的UID", "我的uid"},
    priority=10,
    block=True,
)
uid_delete = on_command(
    "删除UID",
    aliases={"删除uid", "解绑UID", "解绑uid"},
    priority=10,
    block=True,
)
uid_help = on_command(
    "UID帮助",
    aliases={"uid帮助", "游戏UID帮助", "游戏uid帮助"},
    priority=10,
    block=True,
)
group_uid_list = on_command(
    "群UID",
    aliases={"群uid", "群友UID", "群友uid", "UID列表", "uid列表"},
    priority=10,
    block=True,
)
reminder_set = on_command(
    "设置UID提醒",
    aliases={"设置uid提醒"},
    permission=SUPERUSER,
    priority=10,
    block=True,
)
reminder_close = on_command(
    "关闭UID提醒",
    aliases={"关闭uid提醒"},
    permission=SUPERUSER,
    priority=10,
    block=True,
)
reminder_status = on_command(
    "UID提醒状态",
    aliases={"uid提醒状态"},
    priority=10,
    block=True,
)

_repository: UIDRepository | None = None
_repository_path: Path | None = None


def get_repository() -> UIDRepository:
    global _repository, _repository_path

    configured_path = get_plugin_config(Config).game_uid_db_path
    path = Path(configured_path).expanduser() if configured_path else localstore.get_plugin_data_file("uid.db")
    if _repository is None or _repository_path != path:
        _repository = UIDRepository(path)
        _repository_path = path
    return _repository


def get_mentioned_user(message: Message) -> str | None:
    """提取消息中的第一个 QQ @，忽略 @全体成员。"""

    for segment in message:
        if segment.type == "at":
            qq = str(segment.data.get("qq", ""))
            if qq and qq != "all":
                return qq
    return None


def parse_game_argument(text: str) -> tuple[Game | None, str | None]:
    """解析可选的单个游戏参数，并返回面向用户的错误。"""

    parts = text.split()
    if not parts:
        return None, None
    if len(parts) > 1:
        return None, QUERY_USAGE
    game = resolve_game(parts[0])
    if game is None:
        return None, f"不支持游戏“{parts[0]}”。\n支持：星布谷地、原神、星铁、绝区零"
    return game, None


def format_bindings(bindings: dict[str, str], game: Game | None = None) -> str:
    if game is not None:
        uid = bindings.get(game.key)
        return f"{game.name}：{uid}" if uid else f"尚未绑定{game.name} UID。"

    lines = [f"{item.name}：{bindings[item.key]}" for item in GAMES if item.key in bindings]
    return "\n".join(lines) if lines else "尚未绑定任何游戏 UID。"


def format_group_uid_list(
    game: Game,
    members: list[dict],
    bindings: dict[str, str],
    *,
    limit: int,
) -> str:
    lines: list[str] = []
    for member in members:
        user_id = str(member.get("user_id", ""))
        uid = bindings.get(user_id)
        if uid is None:
            continue
        group_card = str(member.get("card") or member.get("nickname") or user_id)
        lines.append(f"{group_card}：{uid}")

    if not lines:
        return f"本群还没有群友绑定{game.name} UID。"
    shown = lines[:limit]
    header = f"本群{game.name} UID 列表（{len(lines)}人）："
    if len(lines) > limit:
        shown.append(f"……另有 {len(lines) - limit} 人未显示，请提高 game_uid_list_limit 配置。")
    return "\n".join([header, *shown])


@uid_bind.handle()
async def handle_bind(event: MessageEvent, args: Message = CommandArg()) -> None:
    parts = args.extract_plain_text().strip().split()
    if len(parts) != 2:
        await uid_bind.finish(BIND_USAGE)

    game = resolve_game(parts[0])
    if game is None:
        await uid_bind.finish(f"不支持游戏“{parts[0]}”。\n支持：星布谷地、原神、星铁、绝区零")

    uid = validate_uid(parts[1])
    if uid is None:
        await uid_bind.finish("UID 必须是 5～20 位半角数字。")

    replaced = await get_repository().set_uid(event.get_user_id(), game.key, uid)
    action = "更新" if replaced else "绑定"
    await uid_bind.finish(f"已{action}{game.name} UID：{uid}")


@uid_query.handle()
async def handle_query(event: MessageEvent, args: Message = CommandArg()) -> None:
    game, error = parse_game_argument(args.extract_plain_text().strip())
    if error:
        await uid_query.finish(error)

    current_user = event.get_user_id()
    target_user = get_mentioned_user(args) or current_user
    bindings = await get_repository().get_all(target_user)
    result = format_bindings(bindings, game)

    if target_user == current_user:
        await uid_query.finish(f"你的 UID：\n{result}")

    message = Message([MessageSegment.at(target_user), MessageSegment.text(f" 的 UID：\n{result}")])
    await uid_query.finish(message)


@uid_delete.handle()
async def handle_delete(event: MessageEvent, args: Message = CommandArg()) -> None:
    parts = args.extract_plain_text().strip().split()
    if len(parts) != 1:
        await uid_delete.finish(DELETE_USAGE)

    game = resolve_game(parts[0])
    if game is None:
        await uid_delete.finish(f"不支持游戏“{parts[0]}”。\n支持：星布谷地、原神、星铁、绝区零")

    deleted = await get_repository().delete_uid(event.get_user_id(), game.key)
    if not deleted:
        await uid_delete.finish(f"你还没有绑定{game.name} UID。")
    await uid_delete.finish(f"已删除{game.name} UID。")


@group_uid_list.handle()
async def handle_group_uid_list(bot: Bot, event: MessageEvent, args: Message = CommandArg()) -> None:
    if not isinstance(event, GroupMessageEvent):
        await group_uid_list.finish("该命令只能在群聊中使用。")

    parts = args.extract_plain_text().strip().split()
    if len(parts) != 1:
        await group_uid_list.finish(GROUP_LIST_USAGE)
    game = resolve_game(parts[0])
    if game is None:
        await group_uid_list.finish(f"不支持游戏“{parts[0]}”。\n支持：星布谷地、原神、星铁、绝区零")

    try:
        members = await bot.get_group_member_list(group_id=event.group_id)
    except Exception as error:
        logger.warning(f"[game_uid] 获取群 {event.group_id} 成员列表失败：{error}")
        await group_uid_list.finish("暂时无法获取本群成员列表，请稍后再试。")

    user_ids = [str(member.get("user_id", "")) for member in members]
    bindings = await get_repository().get_uids_for_users(user_ids, game.key)
    limit = max(1, get_plugin_config(Config).game_uid_list_limit)
    await group_uid_list.finish(format_group_uid_list(game, members, bindings, limit=limit))


@reminder_set.handle()
async def handle_reminder_set(bot: Bot, event: MessageEvent, args: Message = CommandArg()) -> None:
    if not isinstance(event, GroupMessageEvent):
        await reminder_set.finish("该命令只能在群聊中使用。")

    parts = args.extract_plain_text().strip().split()
    if len(parts) != 2:
        await reminder_set.finish(REMINDER_USAGE)
    interval_minutes = parse_duration(parts[0])
    game = resolve_game(parts[1])
    if interval_minutes is None:
        await reminder_set.finish("时间格式不正确或超出范围。\n" + REMINDER_USAGE)
    if game is None:
        await reminder_set.finish(f"不支持游戏“{parts[1]}”。\n支持：星布谷地、原神、星铁、绝区零")

    await get_repository().set_reminder(
        str(event.group_id),
        bot.self_id,
        game.key,
        interval_minutes,
    )
    await reminder_set.finish(
        f"已设置{game.name} UID 定时提醒，每 {format_duration(interval_minutes)}发送一次。\n"
        f"提醒内容：\n{build_reminder_message(game.key)}"
    )


@reminder_close.handle()
async def handle_reminder_close(event: MessageEvent) -> None:
    if not isinstance(event, GroupMessageEvent):
        await reminder_close.finish("该命令只能在群聊中使用。")
    deleted = await get_repository().delete_reminder(str(event.group_id))
    if not deleted:
        await reminder_close.finish("本群尚未开启 UID 定时提醒。")
    await reminder_close.finish("已关闭本群 UID 定时提醒。")


@reminder_status.handle()
async def handle_reminder_status(event: MessageEvent) -> None:
    if not isinstance(event, GroupMessageEvent):
        await reminder_status.finish("该命令只能在群聊中使用。")
    reminder = await get_repository().get_reminder(str(event.group_id))
    if reminder is None:
        await reminder_status.finish("本群尚未开启 UID 定时提醒。")
    game = GAME_BY_KEY[reminder.game]
    await reminder_status.finish(
        f"本群 UID 提醒：已开启\n游戏：{game.name}\n间隔：{format_duration(reminder.interval_minutes)}"
    )


@uid_help.handle()
async def handle_help() -> None:
    await uid_help.finish(
        "游戏 UID 记录\n"
        "/绑定UID <游戏> <UID> — 绑定或更新自己的 UID\n"
        "/游戏UID [游戏] [@群友] — 查询 UID\n"
        "/删除UID <游戏> — 删除自己的绑定\n"
        "/群UID <游戏> — 按“群名片：UID”查看本群列表\n"
        "/设置UID提醒 <间隔> <游戏> — SUPERUSER 开启定时提醒\n"
        "/关闭UID提醒 — SUPERUSER 关闭定时提醒\n"
        "/UID提醒状态 — 查看本群提醒设置\n"
        "/UID帮助 — 查看帮助\n"
        "支持游戏：星布谷地、原神、星铁、绝区零"
    )
