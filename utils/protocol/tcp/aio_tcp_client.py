import asyncio
from typing import Optional

class AioTcpClient:

    def __init__(self, host: str, port: int, timeout=0) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None

    def get_peername(self) -> str:
        """
        Get the host and port of the server in the link
        """
        assert self._writer is not None
        return "{}:{}".format(*self._writer.get_extra_info('peername'))

    def get_sockname(self) -> str:
        """
        Get current client host and port
        """
        assert self._writer is not None
        return "{}:{}".format(*self._writer.get_extra_info('sockname'))

    def is_closing(self) -> bool:
        if self._writer is None:
            return True

        return self._writer.is_closing()

    async def write(self, data) -> None:
        assert self._writer is not None
        self._writer.write(data)
        await self._writer.drain()

    async def writelines(self, data) -> None:
        assert self._writer is not None
        self._writer.writelines(data)
        await self._writer.drain()

    async def close(self) -> None:
        assert self._writer is not None
        self._writer.close()
        await self._writer.wait_closed()

    async def read(self, n=-1) -> bytes:
        assert self._reader is not None
        return await self._reader.read(n)

    async def readline(self) -> bytes:
        assert self._reader is not None
        return await self._reader.readline()

    async def readexactly(self, n) -> bytes:
        assert self._reader is not None
        return await self._reader.readexactly(n)

    async def readuntil(self, separator=b'\n') -> bytes:
        assert self._reader is not None
        return await self._reader.readuntil(separator)

    async def open(self, *, limit=2 ** 16, **kwds):
        if self._timeout:
            try:
                self._reader, self._writer = await asyncio.wait_for(asyncio.open_connection(
                    self._host,
                    self._port,
                    limit=limit,
                    **kwds
                ), timeout=self._timeout)
            except asyncio.TimeoutError as e:
                asyncio.get_running_loop().call_exception_handler({
                    "exception": e
                })

        else:
            await asyncio.open_connection(
                self._host,
                self._port,
                limit=limit,
                **kwds
            )
