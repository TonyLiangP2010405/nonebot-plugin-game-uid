from nonebot import require
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="群友游戏 UID",
    description="记录、汇总和定时播报群友的星布谷地、原神、崩坏：星穹铁道与绝区零 UID",
    usage=(
        "/绑定UID <游戏> <UID>\n"
        "/游戏UID [游戏] [@群友]\n"
        "/删除UID <游戏>\n"
        "/群UID <游戏>\n"
        "/设置UID提醒 <间隔> <游戏>\n"
        "/UID帮助"
    ),
    type="application",
    homepage="https://github.com/TonyLiangP2010405/nonebot-plugin-game-uid",
    config=Config,
    supported_adapters={"~onebot.v11"},
)

require("nonebot_plugin_apscheduler")
require("nonebot_plugin_localstore")

from nonebot_plugin_apscheduler import scheduler  # noqa: E402

from . import commands as commands  # noqa: E402,F401
from .reminders import dispatch_due_reminders  # noqa: E402


@scheduler.scheduled_job(
    "interval",
    minutes=1,
    id="game_uid_dispatch_reminders",
    coalesce=True,
    max_instances=1,
)
async def _dispatch_reminders() -> None:
    await dispatch_due_reminders()
