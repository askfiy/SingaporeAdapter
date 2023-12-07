import enum
import asyncio
import logging
import traceback

from ..tcp.aio_tcp_client import AioTcpClient


from utils import log

ListTuple = list | tuple


def coroutine_safe(coro):
    ins = "lock"

    async def wrapper(self: "AioMcClient", *args, **kwargs):
        if not hasattr(self, ins):
            setattr(self, ins, asyncio.Lock())
        async with getattr(self, ins):
            return await coro(self, *args, **kwargs)
    return wrapper


class SoftComponentCode(enum.Enum):
    data_register = "D*"


class AioMcClient:
    """
    A package based on the Mitsubishi mc protocol that currently only supports D*'s register ASCII reads and writes
    """

    def __init__(self, host: str, port: int, debug: bool = False) -> None:
        self._host = host
        self._port = port
        self._debug = debug
        self._stoped = True
        self._tcp_client = AioTcpClient(host, port, timeout=3)

    def __repr__(self) -> str:
        return "<{} {}:{} id={}>".format(__class__.__name__, self._host, self._port, id(self))

    def is_closing(self) -> bool:
        return self._tcp_client.is_closing()

    def is_stoped(self) -> bool:
        return self._stoped

    async def smart_start(self) -> None:
        if self.is_stoped():
            await self.open()

    async def open(self) -> None:
        await self._tcp_client.open()
        self._stoped = False

        # Since open and smart_start are called under the coroutine_safe decorator
        # So you don't need to consider the security of these 2 methods
        if self._debug:
            logging.debug("Connection {}:{} succesed".format(self._host, self._port))

    @coroutine_safe
    async def close(self) -> None:
        await self._tcp_client.close()
        self._stoped = True

        if self._debug:
            logging.debug("close {}:{}".format(self._host, self._port))

    @coroutine_safe
    async def recv_register(self, start_addr: int, count: int = 1) -> int | tuple:
        await self.smart_start()

        # Build the request body
        request = '500000FF03FF000018001004010000' + SoftComponentCode.data_register.value + \
            str(start_addr).zfill(6) + hex(count)[2:].zfill(4)

        await self._tcp_client.write(bytes(request.encode("utf-8")))

        resp_head = await self._tcp_client.read(22)

        recv_size = 0
        resp_body = b""

        if resp_head == b"":
            raise BrokenPipeError("reception register data failed, broken links")

        resp_body_length = int(resp_head[14:18], base=16) - 4

        while recv_size < resp_body_length:
            resp_body += await self._tcp_client.read(1024)
            recv_size += 1024

        if count == 1:
            return int(resp_body, base=16)

        rr = []
        index = 0
        while len(rr) != len(resp_body) // 4:
            rr.append(int(resp_body[index:index + 4], base=16))
            index += 4
        return tuple(rr)

    @coroutine_safe
    async def send_register(self, start_addr: int, values: int | ListTuple) -> None:
        await self.smart_start()

        req_prefix = "500000FF03FF00"
        req_data = ""
        req_count = ""
        req_length = ""
        req_address = str(start_addr).zfill(6)

        if isinstance(values, int):
            req_count = hex(1)[2:].zfill(4)
            req_data = hex(values)[2:].zfill(4)
        elif isinstance(values, ListTuple):
            req_count = hex(len(values))[2:].zfill(4)
            for value in values:
                req_data += hex(value)[2:].zfill(4)
        else:
            raise TypeError(
                "Unsupported values type, expect <int|tuple|list> but got <{}>".format(
                    type(values).__name__))

        req_suffix = req_address + req_count + req_data
        req_middle = "001014010000" + SoftComponentCode.data_register.value
        req_length = hex(len(req_middle + req_suffix))[2:].zfill(4)

        request = req_prefix + req_length + req_middle + req_suffix

        await self._tcp_client.write(bytes(request.encode("utf-8")))
        # discard 22 pieces of data
        await self._tcp_client.read(22)

    async def safe_send_register(self, start_addr: int, values: int | ListTuple) -> None:
        while True:
            try:
                return await self.send_register(start_addr, values)
            except Exception as e:
                self._stoped = True
                logging.error("{}: {}".format(self, traceback.format_exc()))
            await asyncio.sleep(1)

    async def safe_recv_register(self, start_addr: int, count: int = 1) -> int | tuple:
        while True:
            try:
                return await self.recv_register(start_addr, count)
            except Exception as e:
                self._stoped = True
                logging.error("{}: {}".format(self, traceback.format_exc()))
            await asyncio.sleep(1)
