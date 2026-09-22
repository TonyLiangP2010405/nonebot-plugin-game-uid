import sys

import nonebot


def test_plugin_load() -> None:
    # 其他单元测试会先导入包；NoneBot 要求插件必须由插件管理器首次导入。
    for module_name in [
        name for name in sys.modules if name == "nonebot_plugin_game_uid" or name.startswith("nonebot_plugin_game_uid.")
    ]:
        sys.modules.pop(module_name)
    plugin = nonebot.load_plugin("nonebot_plugin_game_uid")
    assert plugin is not None
    assert plugin.metadata is not None
    assert plugin.metadata.name == "群友游戏 UID"
