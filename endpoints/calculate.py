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
        input = Input.model_validate(params.body)
    except ValidationError as e:
        return func.HttpResponse(
            f"{e}\n{json.dumps(params.body)}",
            status_code=401,
        )
    else:
        return func.HttpResponse(input.model_dump_json())
