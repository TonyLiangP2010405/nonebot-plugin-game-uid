from __future__ import annotations

import re
from typing import Optional

from nonebot import get_bots, logger

from .games import GAME_BY_KEY

DURATION_PATTERN = re.compile(r"^(\d+)(分钟|分|小时|时|天)$")
MIN_INTERVAL_MINUTES = 10
MAX_INTERVAL_MINUTES = 30 * 24 * 60


def parse_duration(value: str) -> Optional[int]:
    """解析 10分钟、6小时、1天一类的时间间隔。"""

    match = DURATION_PATTERN.fullmatch(value.strip())
    if not match:
        return None
    amount = int(match.group(1))
    unit = match.group(2)
    multiplier = 1 if unit in {"分钟", "分"} else 60 if unit in {"小时", "时"} else 24 * 60
    minutes = amount * multiplier
    if not MIN_INTERVAL_MINUTES <= minutes <= MAX_INTERVAL_MINUTES:
        return None
    return minutes


def format_duration(minutes: int) -> str:
    if minutes % (24 * 60) == 0:
        return f"{minutes // (24 * 60)}天"
    if minutes % 60 == 0:
        return f"{minutes // 60}小时"
    return f"{minutes}分钟"


def build_reminder_message(game_key: str) -> str:
    game = GAME_BY_KEY[game_key]
    return (
        f"想查看本群群友的{game.name} UID 并添加游戏好友？\n"
        f"发送 /群UID {game.name}，即可查看群友主动绑定的 UID（群名片：UID）。\n\n"
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
        "/UID帮助 — 查看完整帮助"
    )


async def dispatch_due_reminders(*, now: Optional[float] = None) -> int:
    """发送已到期提醒，返回成功发送数量。"""

    from .commands import get_repository

    repository = get_repository()
    bots = get_bots()
    sent = 0
    for reminder in await repository.get_due_reminders(now=now):
        bot = bots.get(reminder.bot_id)
        if bot is None:
            logger.warning(f"[game_uid] 提醒群 {reminder.group_id} 时机器人 {reminder.bot_id} 不在线")
            continue
        try:
            await bot.call_api(
                "send_group_msg",
                group_id=int(reminder.group_id),
                message=build_reminder_message(reminder.game),
            )
        except Exception as error:
            logger.warning(f"[game_uid] 群 {reminder.group_id} UID 提醒发送失败：{error}")
            continue
        await repository.mark_reminder_sent(reminder.group_id, now=now)
        sent += 1
    return sent
