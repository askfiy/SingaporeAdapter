import json
import os
from typing import (
    Dict,
    Any
)

from .auxiliary import FoxType


class Config(metaclass=FoxType):

    # _SINGLETON: ClassVar[bool] = True

    def __init__(self, conf_path: str, file_encoding: str = "UTF-8", auto_save=False) -> None:
        self._conf_path = conf_path
        self._auto_save = auto_save
        self._conf_dict: Dict[str, Any] = {}
        self._file_encoding = file_encoding

    def __auto_run__(self) -> None:
        self.load()

    def __getitem__(self, key: str) -> Any:
        return self.get_conf_dict()[key]

    def __setitem__(self, key: str, value: Any) -> None:

        self.get_conf_dict()[key] = value

        if self._auto_save:
            self.save()

    def get_conf_path(self) -> str:
        return self._conf_path

    def get_conf_dict(self) -> Dict[str, Any]:
        return self._conf_dict

    def update_conf_dict(self, conf):
        self._conf_dict.update(conf)

    def get_file_encoding(self) -> str:
        return self._file_encoding

    def load(self) -> None:
        err = "File is not exists: {}".format(self.get_conf_path())
        assert os.path.exists(self.get_conf_path()), err

        if not self.get_conf_dict():
            with open(self.get_conf_path(), mode="r", encoding=self.get_file_encoding()) as f:
                self.get_conf_dict().update(
                    json.load(f)
                )

    def save(self) -> None:
        with open(self.get_conf_path(), mode="w", encoding=self.get_file_encoding()) as f:
            json.dump(
                self.get_conf_dict(),
                f,
                indent=2,
                ensure_ascii=True
            )
