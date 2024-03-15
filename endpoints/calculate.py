import azure.functions as func
import logging

from common import Params


def calculate(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Endpoint calculate processed a request.")

    params = Params(req)

    name = params["name"]

    if name:
        return func.HttpResponse(
            f"Hello, {name}. This HTTP triggered function executed successfully."
        )
    else:
        return func.HttpResponse(
            "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
            status_code=200,
        )
