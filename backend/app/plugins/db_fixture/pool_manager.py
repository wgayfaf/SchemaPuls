"""DB Fixture 插件: 目标数据库连接池管理器 (Bounded Connection Pool)

保障即使有上百个接口配置了定时拨测任务同时触发，
也严格通过受控的连接池复用数据库连接，杜绝数据库连接数被打爆。
"""
import asyncio
import logging
from typing import Dict, Optional, Tuple, Any
from contextlib import asynccontextmanager

import asyncpg

from app.plugins.db_fixture.models import MachineDatabase

logger = logging.getLogger("schemapulse.db_fixture.pool")


def _get_ssl_param(ssl_mode: str) -> Any:
    """转换 SSL 模式为 asyncpg 支持的参数"""
    mode = (ssl_mode or "prefer").lower().strip()
    if mode == "require":
        return True
    elif mode == "disable":
        return False
    # prefer: 默认尝试非 SSL, 视目标配置而定
    return False


class DbPoolManager:
    """单例连接池管理器: 按数据库配置缓存与复用 asyncpg.Pool"""

    def __init__(self):
        # 缓存键为 (database_id, host, port, database, username, ssl_mode, pool_size)
        self._pools: Dict[int, asyncpg.Pool] = {}
        self._pool_signatures: Dict[int, Tuple] = {}
        self._lock = asyncio.Lock()

    def _make_signature(self, db: MachineDatabase) -> Tuple:
        return (
            db.id,
            db.host,
            db.port,
            db.database,
            db.username,
            db.password,
            db.ssl_mode,
            db.pool_size
        )

    async def get_pool(self, db: MachineDatabase) -> asyncpg.Pool:
        """获取或创建指定数据库的受控连接池"""
        sig = self._make_signature(db)
        db_id = db.id or 0

        async with self._lock:
            existing_pool = self._pools.get(db_id)
            existing_sig = self._pool_signatures.get(db_id)

            # 若连接池存在且配置未变更且未关闭，直接复用
            if existing_pool and existing_sig == sig and not existing_pool._closed:
                return existing_pool

            # 若配置发生变更或已关闭，先销毁旧连接池
            if existing_pool and not existing_pool._closed:
                try:
                    await existing_pool.close()
                except Exception as e:
                    logger.warning(f"关闭旧数据库连接池异常: {e}")

            # 创建新的受控连接池
            max_size = max(1, min(db.pool_size or 5, 20))
            min_size = 1
            ssl_param = _get_ssl_param(db.ssl_mode)
            connect_timeout = float(db.connect_timeout or 10)

            pool = await asyncpg.create_pool(
                host=db.host,
                port=db.port,
                database=db.database,
                user=db.username,
                password=db.password or "",
                ssl=ssl_param,
                min_size=min_size,
                max_size=max_size,
                timeout=connect_timeout,
                command_timeout=15.0
            )

            self._pools[db_id] = pool
            self._pool_signatures[db_id] = sig
            logger.info(
                f"[DbPoolManager] 成功为数据库 [{db.name} (id={db_id})] 建立连接池, "
                f"容量: {min_size}-{max_size}, 目标: {db.host}:{db.port}/{db.database}"
            )
            return pool

    @asynccontextmanager
    async def acquire_connection(self, db: MachineDatabase):
        """上下文管理器: 从连接池借出连接并保证归还"""
        pool = await self.get_pool(db)
        async with pool.acquire() as conn:
            yield conn

    async def invalidate_pool(self, db_id: int):
        """释放并移除指定数据库的连接池 (用于配置修改或删除)"""
        async with self._lock:
            pool = self._pools.pop(db_id, None)
            self._pool_signatures.pop(db_id, None)
            if pool and not pool._closed:
                try:
                    await pool.close()
                    logger.info(f"[DbPoolManager] 已释放数据库 id={db_id} 的连接池")
                except Exception as e:
                    logger.warning(f"释放连接池异常: {e}")

    async def close_all(self):
        """系统关闭时安全清空所有数据库连接池"""
        async with self._lock:
            for db_id, pool in list(self._pools.items()):
                if pool and not pool._closed:
                    try:
                        await pool.close()
                    except Exception:
                        pass
            self._pools.clear()
            self._pool_signatures.clear()
            logger.info("[DbPoolManager] 所有外部数据库连接池已安全关闭")


# 全局单例管理器
db_pool_manager = DbPoolManager()
