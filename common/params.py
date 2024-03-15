import azure.functions as func
from functools import cache

from typing import Any


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
    def __getitem__(self, index: str) -> Any:
        if (value := self.__headers.get(index)) is not None:
            return value

        if (value := self.__get.get(index)) is not None:
            return value

        value = self.__body

        for i in index.split("."):
            value = value.get(i)
            if value is None:
                break

        return value
