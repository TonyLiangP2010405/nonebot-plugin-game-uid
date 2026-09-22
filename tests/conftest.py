import pytest
from nonebug import NONEBOT_INIT_KWARGS


def pytest_configure(config: pytest.Config) -> None:
    config.stash[NONEBOT_INIT_KWARGS] = {
        "driver": "~none",
        "command_start": ["/"],
        "superusers": {"10001"},
    }
