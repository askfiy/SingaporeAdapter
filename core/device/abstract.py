import abc
import typing

from utils.config import Config


class DeviceConfigAbstract(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def __init__(self, conf: Config):
        pass

    @abc.abstractmethod
    def get_conf(self) -> Config:
        pass

    @abc.abstractmethod
    def get_host(self) -> str:
        pass

    @abc.abstractmethod
    def get_port(self) -> int:
        pass

    @abc.abstractmethod
    def get_name(self) -> str:
        pass

    @abc.abstractmethod
    def get_sig_conf(self):
        pass

    @abc.abstractmethod
    def get_recv_conf(self):
        pass

    @abc.abstractmethod
    def get_send_conf(self):
        pass


class DeviceAbstract(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def __init__(self, name: str, host: str, port: int, conf: Config, debug: bool = False):
        pass

    @abc.abstractmethod
    def get_client(self) -> typing.Any:
        pass

    @abc.abstractmethod
    async def start(self):
        pass

    @abc.abstractmethod
    async def safe_send(self, start_addr: int, values: int | list | tuple) -> None:
        pass

    @abc.abstractmethod
    async def safe_recv(self, start_addr: int, count: int = 1) -> int | tuple:
        pass
