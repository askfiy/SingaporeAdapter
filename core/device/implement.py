from utils.config import Config
from utils.protocol.mc.aio_mc_client import AioMcClient

from . abstract import DeviceAbstract, DeviceConfigAbstract


class BaseDeviceConfig(DeviceConfigAbstract):
    def __init__(self, conf: Config):
        self._conf = conf

    def get_conf(self) -> Config:
        return self._conf

    def get_host(self) -> str:
        return self.get_conf()["HOST"]

    def get_port(self) -> int:
        return self.get_conf()["PORT"]

    def get_name(self) -> str:
        return self.get_conf()["NAME"]

    def get_sig_conf(self):
        return self.get_conf()["SIGNAL"]

    def get_recv_conf(self):
        return self.get_sig_conf()["RECV"]

    def get_send_conf(self):
        return self.get_sig_conf()["SEND"]


class BaseDevice(BaseDeviceConfig, DeviceAbstract):
    _connection_pool = {}

    def __init__(self, conf: Config, debug: bool = False):
        super().__init__(conf)

        self._name: str = conf["NAME"]
        self._host: str = conf["HOST"]
        self._port: int = conf["PORT"]
        self._debug: bool = debug

        # WARN: non-thread-safe - askify 2023-07-12 16:20:41 -
        self._client = __class__._connection_pool.setdefault(
            self._host + str(self._port), AioMcClient(self._host, self._port, debug))

    def get_client(self) -> AioMcClient:
        return self._client

    async def safe_send(self, start_addr: int, values: int | list | tuple) -> None:
        return await self.get_client().safe_send_register(start_addr, values)

    async def safe_recv(self, start_addr: int, count: int = 1) -> int | tuple:
        return await self.get_client().safe_recv_register(start_addr, count)

    async def start(self):
        pass
