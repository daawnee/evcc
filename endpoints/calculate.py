import azure.functions as func
import logging
import json

from common import Params
from models.calculate import Input
from pydantic import ValidationError


def calculate(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Endpoint calculate processed a request.")

    params = Params(req)

    try:
        input = Input(**params.body)
    except ValidationError as e:
        return func.HttpResponse(
            str(e),
            headers={
                "Content-Type": "text/plain; charset=UTF-8",
            },
            status_code=400,
        )
    else:
        return func.HttpResponse(
            input.model_dump_json(),
            headers={
                "Content-Type": "application/json; charset=UTF-8",
            },
        )
