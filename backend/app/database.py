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
                    created_at      TEXT    NOT NULL,
                    data_source     TEXT    DEFAULT 'pipeline_collect',
                    data_fingerprint TEXT   DEFAULT '',
                    source_passed   INTEGER DEFAULT 1,
                    user_discussion_present INTEGER DEFAULT 1
                )
            """)

            try:
                await conn.execute("ALTER TABLE sector_index ADD COLUMN data_source TEXT DEFAULT 'pipeline_collect'")
            except Exception:
                pass
            try:
                await conn.execute("ALTER TABLE sector_index ADD COLUMN data_fingerprint TEXT DEFAULT ''")
            except Exception:
                pass
            try:
                await conn.execute("ALTER TABLE sector_index ADD COLUMN source_passed INTEGER DEFAULT 1")
            except Exception:
                pass
            try:
                await conn.execute("ALTER TABLE sector_index ADD COLUMN user_discussion_present INTEGER DEFAULT 1")
            except Exception:
                pass

            # 原先仅有普通 INDEX，重复 INSERT 同 (sector_code, record_date) 会插入多行，
            # 但 auto_collector 的 _sync_latest_to_db 假设主键约束存在并依赖 UPSERT。
            # 这里补建 UNIQUE 索引（IF NOT EXISTS 保证幂等）。
            # 对于历史遗留的重复数据，先用 DISTINCT 去重后再创建 UNIQUE 索引。
            # 步骤1：清理重复行，每个 (sector_code, record_date) 仅保留最新一条
            await conn.execute("""
                DELETE FROM sector_index
                WHERE id NOT IN (
                    SELECT MAX(id) FROM sector_index
                    GROUP BY sector_code, record_date
                )
            """)
            # 步骤2：将原普通索引替换为 UNIQUE 索引
            await conn.execute("DROP INDEX IF EXISTS idx_sector_date")
            await conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_sector_date ON sector_index(sector_code, record_date)"
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

            # 审计日志表扩展字段（数据真实性排查专项）：
            # - data_fingerprint: 关联本次采集批次的数据指纹（来自 sector_index.data_fingerprint）
            # - sector_code: 板块级操作时的板块代码
            # - sector_count: 批量操作涉及的板块数
            # - detail: 自由文本明细（如跳过原因、失败原因）
            # 逐字段尝试添加，已存在则跳过（SQLite 不支持 ADD COLUMN IF NOT EXISTS）
            for col_def in (
                ("data_fingerprint", "TEXT DEFAULT ''"),
                ("sector_code", "TEXT DEFAULT ''"),
                ("sector_count", "INTEGER DEFAULT 0"),
                ("detail", "TEXT DEFAULT ''"),
            ):
                try:
                    await conn.execute(f"ALTER TABLE audit_logs ADD COLUMN {col_def[0]} {col_def[1]}")
                except Exception:
                    pass

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS system_config (
                    key     TEXT PRIMARY KEY,
                    value   TEXT,
                    updated_at TEXT NOT NULL
                )
            """)

    async def insert_sector_index(self, data: Dict) -> int:
        """插入或更新板块指数记录（UPSERT），包含数据来源审计字段。"""
        now = datetime.now().isoformat()
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                """INSERT INTO sector_index
                   (sector_code, sector_name, index_value, buy_index, sell_index,
                    newbie_ratio, total_posts, record_date, created_at,
                    data_source, data_fingerprint, source_passed, user_discussion_present)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(sector_code, record_date) DO UPDATE SET
                    sector_name  = excluded.sector_name,
                    index_value  = excluded.index_value,
                    buy_index    = excluded.buy_index,
                    sell_index   = excluded.sell_index,
                    newbie_ratio = excluded.newbie_ratio,
                    total_posts  = excluded.total_posts,
                    created_at   = excluded.created_at,
                    data_source  = excluded.data_source,
                    data_fingerprint = excluded.data_fingerprint,
                    source_passed = excluded.source_passed,
                    user_discussion_present = excluded.user_discussion_present""",
                (
                    data["sector_code"], data["sector_name"],
                    data["index_value"], data.get("buy_index", 0),
                    data.get("sell_index", 0), data.get("newbie_ratio", 0),
                    data.get("total_posts", 0), data["record_date"], now,
                    data.get("data_source", "pipeline_collect"),
                    data.get("data_fingerprint", ""),
                    1 if data.get("source_passed", True) else 0,
                    1 if data.get("user_discussion_present", True) else 0,
                )
            )
            return cursor.lastrowid

    async def get_latest_sector_index(self, sector_code: str = None) -> List[Dict]:
        async with self.get_connection() as conn:
            if sector_code:
                cursor = await conn.execute(
                    """SELECT * FROM sector_index WHERE sector_code = ?
                       AND NOT (COALESCE(total_posts, 0) = 0 OR (COALESCE(index_value, 0) = 0 AND COALESCE(buy_index, 0) = 0 AND COALESCE(sell_index, 0) = 0))
                       ORDER BY record_date DESC LIMIT 1""",
                    (sector_code,)
                )
            else:
                cursor = await conn.execute(
                    """SELECT s.* FROM sector_index s
                       INNER JOIN (
                           SELECT sector_code, MAX(record_date) as max_date
                           FROM sector_index
                           WHERE NOT (COALESCE(total_posts, 0) = 0 OR (COALESCE(index_value, 0) = 0 AND COALESCE(buy_index, 0) = 0 AND COALESCE(sell_index, 0) = 0))
                           GROUP BY sector_code
                       ) latest ON s.sector_code = latest.sector_code
                       AND s.record_date = latest.max_date
                       WHERE NOT (COALESCE(s.total_posts, 0) = 0 OR (COALESCE(s.index_value, 0) = 0 AND COALESCE(s.buy_index, 0) = 0 AND COALESCE(s.sell_index, 0) = 0))"""
                )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_sector_history(self, sector_code: str, days: int = 30) -> List[Dict]:
        async with self.get_connection() as conn:
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            cursor = await conn.execute(
                """SELECT * FROM sector_index
                   WHERE sector_code = ? AND record_date >= ?
                     AND NOT (COALESCE(total_posts, 0) = 0 OR (COALESCE(index_value, 0) = 0 AND COALESCE(buy_index, 0) = 0 AND COALESCE(sell_index, 0) = 0))
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
                     AND NOT (COALESCE(total_posts, 0) = 0 OR (COALESCE(index_value, 0) = 0 AND COALESCE(buy_index, 0) = 0 AND COALESCE(sell_index, 0) = 0))
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
        """记录审计日志。

        支持的关键字段：
            endpoint: 接口或模块名
            ip_addr: 操作来源 IP
            duration_ms: 耗时
            status: success / failed / degraded 等
            data_fingerprint: 本次操作关联的数据指纹（用于追溯数据批次）
            sector_code: 板块级操作时的板块代码
            sector_count: 批量操作涉及的板块数
            detail: 自由文本明细
        """
        now = datetime.now().isoformat()
        async with self.get_connection() as conn:
            await conn.execute(
                """INSERT INTO audit_logs
                   (username, action, endpoint, ip_addr, duration_ms, status, created_at,
                    data_fingerprint, sector_code, sector_count, detail)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    username, action,
                    kwargs.get("endpoint", ""),
                    kwargs.get("ip_addr", ""),
                    kwargs.get("duration_ms", 0),
                    kwargs.get("status", "success"),
                    now,
                    kwargs.get("data_fingerprint", ""),
                    kwargs.get("sector_code", ""),
                    kwargs.get("sector_count", 0),
                    kwargs.get("detail", ""),
                )
            )


db = Database.get_instance()
