import os
import json
import argparse
from typing import Dict, Any, ClassVar, Optional

from .auxiliary import FoxType


class CommandArgsParse(metaclass=FoxType):

    _SINGLETON: ClassVar[bool] = True

    _ARGUMENTPARAMS_KEY: ClassVar[str] = "params"
    _ARGUMENTARGUMENTS_KEY: ClassVar[str] = "arguments"
    _ARGUMENTSUBPARSERS_KEY: ClassVar[str] = "subparsers"
    _ARGUMENTPARSERBASIC_KEY: ClassVar[str] = "basic_definition"

    def __init__(self, conf_path: str) -> None:
        self._conf_path = conf_path
        self._conf_dict: Dict[str, Any] = {}
        self._argparse: Optional[argparse.ArgumentParser] = None

    def __auto_run__(self) -> None:
        self._conf_settings()
        self._load_argparse()

    def get_conf_path(self) -> str:
        return self._conf_path

    def get_conf_dict(self) -> Dict[str, Any]:
        return self._conf_dict

    def get_argparse(self) -> argparse.ArgumentParser:
        assert self._argparse, "{} self._argparse is None".format(self)
        return self._argparse

    def get_parse_args(self):
        return self.get_argparse().parse_args()

    def _conf_settings(self) -> None:
        self._parse_conf()
        self._update_conf()

    def _parse_conf(self) -> None:
        err = "File is not exists: {}".format(self.get_conf_path())
        assert os.path.exists(self.get_conf_path()), err

        with open(self.get_conf_path(), mode="r", encoding="UTF-8") as f:
            self.get_conf_dict().update(json.load(f))

    def _update_conf(self) -> None:
        arguments = self.get_conf_dict()[__class__._ARGUMENTARGUMENTS_KEY]
        for args_conf in arguments:
            type_value = args_conf.get("type")
            if type_value:
                args_conf["type"] = eval(type_value)

    def _load_argparse(self) -> None:

        parser_conf = self.get_conf_dict()[__class__._ARGUMENTPARSERBASIC_KEY]

        self._argparse = argparse.ArgumentParser(
            **parser_conf
        )

        # load subcommand
        subparsers_conf = self.get_conf_dict()[__class__._ARGUMENTSUBPARSERS_KEY]

        subparsers = self._argparse.add_subparsers(dest=__class__._ARGUMENTSUBPARSERS_KEY)

        for parsers_conf in subparsers_conf:
            subparsers.add_parser(**parsers_conf)

        # load parameters
        arguments_conf = self.get_conf_dict()[__class__._ARGUMENTARGUMENTS_KEY]

        for args_conf in arguments_conf:
            params = args_conf.pop(__class__._ARGUMENTPARAMS_KEY)
            self._argparse.add_argument(
                *params,
                **args_conf
            )
