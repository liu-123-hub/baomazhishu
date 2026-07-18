"""基于 aiosqlite 的异步 SQLite 数据库操作。"""
import json
import aiosqlite
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from .config import settings


class Database:
    """数据库管理类（单例）。"""

    _instance = None

    def __init__(self):
        self.db_path = str(settings.DB_PATH)

    @classmethod
    def get_instance(cls) -> "Database":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @asynccontextmanager
    async def get_connection(self):
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = aiosqlite.Row
        try:
            yield conn
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
        finally:
            await conn.close()

    async def init_database(self):
        async with self.get_connection() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sector_index (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    sector_code     TEXT    NOT NULL,
                    sector_name     TEXT    NOT NULL,
                    index_value     REAL    NOT NULL,
                    buy_index       REAL    DEFAULT 0,
                    sell_index      REAL    DEFAULT 0,
                    newbie_ratio    REAL    DEFAULT 0,
                    total_posts     INTEGER DEFAULT 0,
                    record_date     TEXT    NOT NULL,
                    created_at      TEXT    NOT NULL
                )
            """)

            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sector_date ON sector_index(sector_code, record_date)"
            )

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    username        TEXT    NOT NULL,
                    action          TEXT    NOT NULL,
                    endpoint        TEXT,
                    ip_addr         TEXT,
                    duration_ms     INTEGER DEFAULT 0,
                    status          TEXT    DEFAULT 'success',
                    created_at      TEXT    NOT NULL
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS system_config (
                    key     TEXT PRIMARY KEY,
                    value   TEXT,
                    updated_at TEXT NOT NULL
                )
            """)

    async def insert_sector_index(self, data: Dict) -> int:
        now = datetime.now().isoformat()
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                """INSERT INTO sector_index
                   (sector_code, sector_name, index_value, buy_index, sell_index,
                    newbie_ratio, total_posts, record_date, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    data["sector_code"], data["sector_name"],
                    data["index_value"], data.get("buy_index", 0),
                    data.get("sell_index", 0), data.get("newbie_ratio", 0),
                    data.get("total_posts", 0), data["record_date"], now
                )
            )
            return cursor.lastrowid

    async def get_latest_sector_index(self, sector_code: str = None) -> List[Dict]:
        async with self.get_connection() as conn:
            if sector_code:
                cursor = await conn.execute(
                    """SELECT * FROM sector_index WHERE sector_code = ?
                       ORDER BY record_date DESC LIMIT 1""",
                    (sector_code,)
                )
            else:
                cursor = await conn.execute(
                    """SELECT s.* FROM sector_index s
                       INNER JOIN (
                           SELECT sector_code, MAX(record_date) as max_date
                           FROM sector_index GROUP BY sector_code
                       ) latest ON s.sector_code = latest.sector_code
                       AND s.record_date = latest.max_date"""
                )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_sector_history(self, sector_code: str, days: int = 30) -> List[Dict]:
        async with self.get_connection() as conn:
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            cursor = await conn.execute(
                """SELECT * FROM sector_index
                   WHERE sector_code = ? AND record_date >= ?
                   ORDER BY record_date ASC""",
                (sector_code, start_date)
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_all_sectors_history(self, days: int = 30) -> Dict[str, List]:
        async with self.get_connection() as conn:
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            cursor = await conn.execute(
                """SELECT * FROM sector_index WHERE record_date >= ?
                   ORDER BY sector_code, record_date ASC""",
                (start_date,)
            )
            rows = await cursor.fetchall()
            result = {}
            for row in rows:
                r = dict(row)
                code = r["sector_code"]
                if code not in result:
                    result[code] = []
                result[code].append(r)
            return result

    async def add_audit_log(self, username: str, action: str, **kwargs):
        now = datetime.now().isoformat()
        async with self.get_connection() as conn:
            await conn.execute(
                """INSERT INTO audit_logs
                   (username, action, endpoint, ip_addr, duration_ms, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    username, action,
                    kwargs.get("endpoint", ""),
                    kwargs.get("ip_addr", ""),
                    kwargs.get("duration_ms", 0),
                    kwargs.get("status", "success"),
                    now
                )
            )


db = Database.get_instance()
