import asyncio
from typing import Any, Optional, Dict

import asyncpg

from .auxiliary import FoxType


class AioPostgresql(metaclass=FoxType):
    def __init__(self, conf_dict: Dict[str, Any]) -> None:
        self.conf_dict = conf_dict
        self.connect_pool: Optional[asyncpg.Pool] = None

    def get_conf_dict(self) -> Dict[str, Any]:
        return self.conf_dict

    def __auto_run__(self):
        self.config_handle()

    def config_handle(self):
        conf = {}
        for k, v in self.conf_dict.items():
            conf[k.lower()] = v

        self.conf_dict = conf

    async def get_connect_pool(self) -> asyncpg.Pool:
        from . import log
        while self.connect_pool is None:
            try:
                self.connect_pool = await asyncpg.create_pool(**self.get_conf_dict())
            except Exception as e:
                log.error("{} connection pool create faild, retrying ..\n{}".format(self, e))
                await asyncio.sleep(3)
        return self.connect_pool

    async def execute(self, query: str, *args, timeout: Optional[float] = None) -> str:
        async with (await self.get_connect_pool()).acquire() as conn:
            async with conn.transaction():
                return await conn.execute(query, *args, timeout=timeout)

    async def executemany(self, command: str, args, *, timeout: Optional[float] = None):
        async with (await self.get_connect_pool()).acquire() as conn:
            async with conn.transaction():
                return await conn.execute(command, *args, timeout=timeout)

    async def fetch(self, query, *args, timeout=None, record_class=None) -> list:
        return await (await self.get_connect_pool())\
            .fetch(query, *args, timeout=timeout, record_class=record_class)

    async def fetchval(self, query, *args, column=0, timeout=None):
        return await (await self.get_connect_pool())\
            .fetchval(query, *args, column=column, timeout=timeout)

    async def fetchrow(self, query, *args, timeout=None, record_class=None):
        return await (await self.get_connect_pool())\
            .fetchrow(query, *args, timeout=timeout, record_class=record_class)
