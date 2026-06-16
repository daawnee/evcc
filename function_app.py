import azure.functions as func
import endpoints

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(
    route="calculate",
    methods=["GET", "POST"],
)
def calculate(req: func.HttpRequest) -> func.HttpResponse:
    return endpoints.calculate(req=req)


@app.route(
    route="models",
    methods=["GET"],
)
def models(req: func.HttpRequest) -> func.HttpResponse:
    return endpoints.models(req=req)


@app.route(
    route="car/{model_id}",
    methods=["GET"],
)
def car(req: func.HttpRequest) -> func.HttpResponse:
    return endpoints.car(req=req)


@app.route(
    route="photo/{model_id}",
    methods=["GET"],
)
def photo(req: func.HttpRequest) -> func.HttpResponse:
    return endpoints.photo(req=req)


# Catch-all: serve the built Vue SPA. Literal routes above take precedence over this wildcard.
@app.route(
    route="{*path}",
    methods=["GET"],
)
def static_files(req: func.HttpRequest) -> func.HttpResponse:
    return endpoints.static_files(req=req)
