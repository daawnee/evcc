import azure.functions as func
from functools import cache

from typing import Any, Optional, Dict


class Params:
    def __init__(self, req: func.HttpRequest) -> None:
        self.__headers = req.headers
        self.__get = req.params
        try:
            self.__body = req.get_json()
        except ValueError:
            pass
        else:
            self.__body = {}

    @cache
    def __getitem__(self, index: str) -> Optional[Any]:
        if (value := self.__headers.get(index)) is not None:
            return value

        if (value := self.__get.get(index)) is not None:
            return value

        value = self.__body

        for i in index.split("."):
            try:
                value = value[i]
            except (TypeError, KeyError):
                value = None
                break

        return value

    @property
    def headers(self) -> Dict[str, str]:
        return self.__headers

    @property
    def get(self) -> Dict[str, str]:
        return self.__get

    @property
    def body(self) -> Dict[str, Any]:
        return self.__body
