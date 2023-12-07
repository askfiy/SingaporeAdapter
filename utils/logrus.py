import os
import json
from logging import Logger
from logging import getLogger
from logging.config import dictConfig
from typing import ClassVar, Dict, Any, Optional


from .auxiliary import FoxType


class Logrus(metaclass=FoxType):

    _SINGLETON: ClassVar[bool] = True

    def __init__(self, conf_path: str, logger_name: str = "logger") -> None:
        self._conf_path = conf_path
        self._logger_name = logger_name
        self._conf_dict: Dict[str, Any] = {}
        self._logger: Optional[Logger] = None

    def __auto_run__(self) -> None:
        self._parse_conf()
        self._logger = getLogger(self.get_logger_name())

    def get_logger(self) -> Logger:
        assert self._logger, "{} self._logger is None".format(self)
        return self._logger

    def get_logger_name(self) -> str:
        return self._logger_name

    def get_conf_path(self) -> str:
        return self._conf_path

    def get_conf_dict(self) -> Dict[str, Any]:
        return self._conf_dict

    def _parse_conf(self) -> None:
        err = "File is not exists: {}".format(self.get_conf_path())
        assert os.path.exists(self.get_conf_path()), err

        with open(self.get_conf_path(), mode="r", encoding="UTF-8") as f:
            self.get_conf_dict().update(json.load(f))

        for handler in self.get_conf_dict().get("handlers", {}).values():
            handler: Dict[str, Any]
            filename_full_path: Optional[str] = handler.get("filename")

            if filename_full_path:
                dirname_full_path: str = os.path.dirname(filename_full_path)

                if not os.path.exists(dirname_full_path):
                    os.makedirs(dirname_full_path, exist_ok=True)

        dictConfig(self.get_conf_dict())
