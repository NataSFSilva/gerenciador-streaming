import json
import logging
from datetime import datetime

import db
import logging_loki
from flask import Flask, request
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (BatchSpanProcessor,
                                            ConsoleSpanExporter)
from prometheus_flask_exporter import PrometheusMetrics

# Configuração do OpenTelemetry
resource = Resource.create({SERVICE_NAME: "flask-jornada"})
trace.set_tracer_provider(TracerProvider(resource=resource))

# Configuração do OTLP Exporter com HTTP/JSON
otlp_exporter = OTLPSpanExporter(
    endpoint="http://172.21.0.4:4318",
    headers={},
)
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Configução da API
app = Flask(__name__)
app.config["JSONIFY_MIMETYPE"] = "application/json; charset=utf-8"
app.json.sort_keys = False

# Configução das métricas
metrics = PrometheusMetrics(app)
metrics.info("app_info", "Application info", version="1.0")

# Configuração dos logs
formatter = logging.basicConfig(
    level=logging.INFO, filename="aplication.log", format="%(asctime)s - %(levelname)s %(message)s"
)
logging.config
logger = logging.getLogger(__name__)
handler = logging_loki.LokiHandler(
    url="http://grafana-loki-hml.dock.tech/loki/api/v1/push",
    tags={"jornada": "loki"},
    version="1",
)
handler.setFormatter(formatter)
logger.addHandler(handler)


# Instrumentando Flask
FlaskInstrumentor().instrument_app(app)

def responseSuccess(stts: int, msg: str, dt=None):
    response = {
        "status": stts,
        "datetime": datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
        "message": msg,
    }

    if dt is not None:
        response["data"] = dt

    return response, stts


def responseError(stts: int, msg: str):
    response = {
        "status": stts,
        "datetime": datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
        "message": msg,
    }
    return response, stts


@app.route("/filmes", methods=["GET", "POST"])
def getPost():
    with trace.get_tracer(__name__).start_as_current_span("flask-jonrada-manual"):
        logging.info("Function getPost() called")
        if request.method == "GET":
            logging.info("GET request in the endpoint /filmes")

            filmesList = db.selectAll()

            if len(filmesList) == 0:
                logging.info("Database query returned empty content")
                return responseSuccess(204, "No content")

            logging.debug("Data: " + str(filmesList))
            logging.info("Success query")
            return responseSuccess(200, "Success request", filmesList)

        elif request.method == "POST":
            logging.info("POST request in the endpoint /filmes")
            novoFilme = request.json

            if (
                novoFilme["titulo"] == None
                or novoFilme["direcao"] == None
                or novoFilme["genero"] == None
                or novoFilme["lancamento"] == None
            ):
                logging.warning("Mandatory data not provided")
                return responseError(400, "Bad request")

            retorno = db.insert(novoFilme)

            logging.debug("Data: " + json.dumps(retorno))
            logging.info("Data added to the database")
            return responseSuccess(201, "Successful database insertion", retorno)


@app.route("/filmes/<int:id>", methods=["GET", "PUT", "DELETE"])
def opsById(id: int):
    with trace.get_tracer(__name__).start_as_current_span("flask-jonrada-manual"):
        logging.info("Function opsById() called")
        if request.method == "GET":
            logging.info("GET request in the endpoint /filmes/<int:id>")
            filme = db.selectById(id)

            if filme == None:
                logging.warning("Data not found")
                return responseError(404, "Value not found")

            logging.debug("Data: " + json.dumps(filme))
            logging.info("Found value")
            return responseSuccess(200, "Success request", filme)
        elif request.method == "PUT":
            logging.info("PUT request in the endpoint /filmes/<int:id>")
            response = db.update(id, request.json)

            if response == False:
                logging.warning("Mandatory data not provided")
                return responseError(400, "Bad request")

            logging.info(f"Data of ID {id} updated")
            return responseSuccess(204, "Value updated successfully")
        elif request.method == "DELETE":
            logging.info("DELETE request in the endpoint /filmes/<int:id>")
            response = db.delete(id)

            if response == False:
                logging.warning("Data not found")
                return responseError(404, "Value not found")

            logging.info(f"Data of ID {id} deleted")
            return responseSuccess(204, "Value deleted successfully", None)


@app.route("/filmes/diretor/<string:d>", methods=["GET"])
def getByDiretor(d):
    with trace.get_tracer(__name__).start_as_current_span("flask-jonrada-manual"):
        logging.info("Function getByDiretor() called")
        logging.info("GET request in the endpoint /filmes/diretor/<string:d>")
        filmes = db.selectByDiretor(d)

        if filmes == None:
            logging.warning("Data not found")
            return responseError(404, "Value not found")

        logging.debug("Data: " + str(filmes))
        logging.info("Found value")
        return responseSuccess(200, "Success request", filmes)


@app.route("/filmes/genero/<string:g>", methods=["GET"])
def getByGenero(g):
    with trace.get_tracer(__name__).start_as_current_span("flask-jonrada-manual"):
        logging.info("Function getByGenero() called")
        logging.info("GET request in the endpoint /filmes/genero/<string:g>")
        filmes = db.selectByGenero(g)

        if filmes == None:
            logging.warning("Data not found")
            return responseError(404, "Value not found")

        logging.debug("Data: " + str(filmes))
        logging.info("Success request")
        return responseSuccess(200, "Found value with sucess", filmes)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)