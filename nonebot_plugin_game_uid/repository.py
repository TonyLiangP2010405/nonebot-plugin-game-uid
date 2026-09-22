from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path

import aiosqlite


@dataclass(frozen=True)
class GroupReminder:
    group_id: str
    bot_id: str
    game: str
    interval_minutes: int
    next_run_at: float


class UIDRepository:
    """基于 SQLite 的 UID 存储。"""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def initialize(self) -> None:
        if self._initialized:
            return

        async with self._init_lock:
            if self._initialized:
                return
            await asyncio.to_thread(self.db_path.parent.mkdir, parents=True, exist_ok=True)
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS uid_bindings (
                        platform_user_id TEXT NOT NULL,
                        game TEXT NOT NULL,
                        uid TEXT NOT NULL,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (platform_user_id, game)
                    )
                    """
                )
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS group_reminders (
                        group_id TEXT PRIMARY KEY,
                        bot_id TEXT NOT NULL,
                        game TEXT NOT NULL,
                        interval_minutes INTEGER NOT NULL,
                        next_run_at REAL NOT NULL
                    )
                    """
                )
                await db.commit()
            self._initialized = True

    async def set_uid(self, platform_user_id: str, game: str, uid: str) -> bool:
        """新增或更新 UID；返回 True 表示替换了旧绑定。"""

        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT 1 FROM uid_bindings WHERE platform_user_id = ? AND game = ?",
                (platform_user_id, game),
            )
            existed = await cursor.fetchone() is not None
            await cursor.close()
            await db.execute(
                """
                INSERT INTO uid_bindings (platform_user_id, game, uid)
                VALUES (?, ?, ?)
                ON CONFLICT(platform_user_id, game) DO UPDATE SET
                    uid = excluded.uid,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (platform_user_id, game, uid),
            )
            await db.commit()
        return existed

    async def get_uid(self, platform_user_id: str, game: str) -> str | None:
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT uid FROM uid_bindings WHERE platform_user_id = ? AND game = ?",
                (platform_user_id, game),
            )
            row = await cursor.fetchone()
            await cursor.close()
        return str(row[0]) if row else None

    async def get_all(self, platform_user_id: str) -> dict[str, str]:
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT game, uid FROM uid_bindings WHERE platform_user_id = ?",
                (platform_user_id,),
            )
            rows = await cursor.fetchall()
            await cursor.close()
        return {str(game): str(uid) for game, uid in rows}

    async def get_uids_for_users(self, platform_user_ids: list[str], game: str) -> dict[str, str]:
        """批量获取一组用户的指定游戏 UID。"""

        await self.initialize()
        if not platform_user_ids:
            return {}

        result: dict[str, str] = {}
        async with aiosqlite.connect(self.db_path) as db:
            for start in range(0, len(platform_user_ids), 900):
                chunk = platform_user_ids[start : start + 900]
                placeholders = ",".join("?" for _ in chunk)
                cursor = await db.execute(
                    f"""
                    SELECT platform_user_id, uid
                    FROM uid_bindings
                    WHERE game = ? AND platform_user_id IN ({placeholders})
                    """,  # noqa: S608 - placeholders are generated locally, values remain parameterized
                    (game, *chunk),
                )
                rows = await cursor.fetchall()
                await cursor.close()
                result.update({str(user_id): str(uid) for user_id, uid in rows})
        return result

    async def delete_uid(self, platform_user_id: str, game: str) -> bool:
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM uid_bindings WHERE platform_user_id = ? AND game = ?",
                (platform_user_id, game),
            )
            deleted = cursor.rowcount > 0
            await cursor.close()
            await db.commit()
        return deleted

    async def set_reminder(
        self,
        group_id: str,
        bot_id: str,
        game: str,
        interval_minutes: int,
        *,
        now: float | None = None,
    ) -> None:
        await self.initialize()
        current_time = time.time() if now is None else now
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO group_reminders (group_id, bot_id, game, interval_minutes, next_run_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(group_id) DO UPDATE SET
                    bot_id = excluded.bot_id,
                    game = excluded.game,
                    interval_minutes = excluded.interval_minutes,
                    next_run_at = excluded.next_run_at
                """,
                (group_id, bot_id, game, interval_minutes, current_time + interval_minutes * 60),
            )
            await db.commit()

    async def get_reminder(self, group_id: str) -> GroupReminder | None:
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT group_id, bot_id, game, interval_minutes, next_run_at
                FROM group_reminders
                WHERE group_id = ?
                """,
                (group_id,),
            )
            row = await cursor.fetchone()
            await cursor.close()
        return GroupReminder(*row) if row else None

    async def get_due_reminders(self, *, now: float | None = None) -> list[GroupReminder]:
        await self.initialize()
        current_time = time.time() if now is None else now
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT group_id, bot_id, game, interval_minutes, next_run_at
                FROM group_reminders
                WHERE next_run_at <= ?
                ORDER BY next_run_at
                """,
                (current_time,),
            )
            rows = await cursor.fetchall()
            await cursor.close()
        return [GroupReminder(*row) for row in rows]

    async def mark_reminder_sent(self, group_id: str, *, now: float | None = None) -> None:
        await self.initialize()
        current_time = time.time() if now is None else now
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE group_reminders
                SET next_run_at = ? + interval_minutes * 60
                WHERE group_id = ?
                """,
                (current_time, group_id),
            )
            await db.commit()

    async def delete_reminder(self, group_id: str) -> bool:
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM group_reminders WHERE group_id = ?", (group_id,))
            deleted = cursor.rowcount > 0
            await cursor.close()
            await db.commit()
        return deleted
