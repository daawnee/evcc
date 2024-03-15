import azure.functions as func
import endpoints

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(
    route="calculate",
    methods=["GET", "POST"],
)
def calculate(req: func.HttpRequest) -> func.HttpResponse:
    return endpoints.calculate(req=req)
