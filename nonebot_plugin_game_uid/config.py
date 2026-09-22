from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Config(BaseModel):
    """插件配置。"""

    game_uid_db_path: Optional[str] = None
    game_uid_list_limit: int = 100
