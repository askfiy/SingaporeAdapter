import traceback
import asyncio
import logging
from asyncio.base_events import Server
from typing import Tuple, Type, Optional


class AioTcpRequest:
    """
    A wrapper based on asyncio.StreamReader and asyncio.StreamWriter
    The request class
    """

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.reader = reader
        self.writer = writer

        self.client_address = writer.get_extra_info('peername')
        self.server_address = writer.get_extra_info('socket')

    def get_peername(self) -> str:
        """
        Get the host and port of the client in the link
        """
        return "{}:{}".format(*self.client_address)

    def get_sockname(self) -> str:
        """
        Get the host and port of the server side in the link
        """
        return "{}:{}".format(self.server_address)

    def is_closing(self) -> bool:
        return self.writer.is_closing()

    async def write(self, data) -> None:
        self.writer.write(data)
        await self.writer.drain()

    async def writelines(self, data) -> None:
        self.writer.writelines(data)
        await self.writer.drain()

    async def close(self) -> None:
        self.writer.close()
        await self.writer.wait_closed()

    async def read(self, n=-1) -> bytes:
        return await self.reader.read(n)

    async def readline(self) -> bytes:
        return await self.reader.readline()

    async def readexactly(self, n) -> bytes:
        return await self.reader.readexactly(n)

    async def readuntil(self, separator=b'\n') -> bytes:
        return await self.reader.readuntil(separator)


class AioBaseRequestHandler:
    """
    An asyncio-based base class for handling links
    Inheritance can be used by overriding the handle method
    """

    def __init__(self, request: AioTcpRequest, server: Server) -> None:
        self.request = request
        self.server = server

    async def setup(self) -> None:
        """
        Hook function, called before handle
        """
        pass

    async def handle(self) -> None:
        """
        Hook function for handling links

        Example:
        --------

            logging.info("client {} connected".format(self.request.get_peername()))

            while True:
                try:
                    rr = await self.request.read(1024)

                    if not rr:
                        raise ConnectionError("client {} disconnect".format(self.request.get_peername()))

                except Exception as e:
                    if isinstance(e, ConnectionError):
                        logging.error(e)
                    else:
                        logging.error(traceback.format_exc())
                    break

                await self.request.write(b"AioTcpServer")

            await self.request.close()

        --------
        """
        pass

    async def finish(self) -> None:
        """
        Hook function, called after handle
        """
        pass


class AioTcpServer:
    """
    An asyncio based TCP server
    Initiated via the serve_forever method

    Example:
    --------

    import asyncio

    from utils.aio_tcp_server import AioTcpServer, AioBaseRequestHandler


    class RequestHandler(AioBaseRequestHandler):
        async def handle(self) -> None:
            pass


    asyncio.run(
        AioTcpServer(
            server_address=("localhost", 8000),
            request_handler_class=RequestHandler
        ).serve_forever()
    )

    --------
    """

    def __init__(self, server_address: Tuple[str, int], request_handler_class: Type[AioBaseRequestHandler]) -> None:

        assert issubclass(request_handler_class, AioBaseRequestHandler), \
            "{}.__init__() method parameter `request_handler_class` must is {} sub class". \
            format(self, AioBaseRequestHandler)

        self.server_address = server_address
        self.request_handler_class = request_handler_class
        self.server: Optional[Server] = None

    async def finish_request(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        request = AioTcpRequest(reader, writer)

        try:
            assert self.server is not None, "{} `self.server` is None".format(self)
            handler = self.request_handler_class(request, self.server)
            try:
                await handler.setup()
                await handler.handle()
            finally:
                await handler.finish()
        except Exception:
            logging.error(traceback.format_exc())
        finally:
            if not request.is_closing():
                await request.close()

    async def serve_forever(self) -> None:

        self.server = await asyncio.start_server(
            self.finish_request,
            *self.server_address
        )

        async with self.server:
            logging.debug("Forever server {}:{}".format(*self.server_address))
            await self.server.serve_forever()
