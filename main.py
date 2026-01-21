import logging
import sys
import traceback
import uuid
import os
from app import create_app
from flask import Flask, request, jsonify
from app.graph import build_graph
from app.schemas.request import ScanRequest
from app.schemas.response import ScanResponse
from config.settings import settings

# === CONFIGURACIÓN GLOBAL DE LOGGING ===
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    stream=sys.stdout,
    force=True,  # pisa cualquier config previa (útil con Flask)
)
logger = logging.getLogger(__name__)

app = create_app()

# Construimos el grafo una vez al arrancar
graph = build_graph(settings)

@app.get("/health")
def health():
    return jsonify({"status": "ok"})

@app.post("/agent/scan")
def scan():
    try:
        payload = request.get_json(force=True, silent=False)
        req = ScanRequest.model_validate(payload)

        # Generamos el trace_id automáticamente si no lo ha proporcionado el cliente
        trace_id = req.trace_id if req.trace_id else str(uuid.uuid4())  # Si no hay trace_id, generamos uno nuevo

        # Semilla de estado inicial para el grafo
        state = {"client_id": req.client_id, "trace_id": trace_id}
        logger.info("Graph.run() START client_id=%s trace_id=%s", req.client_id, trace_id)

        # Ejecutamos el root agent (bloqueante)
        msg, final_state = graph.run(state=state)

        logger.info(
            "Graph.run() END client_id=%s trace_id=%s last_msg_len=%s state_keys=%s",
            req.client_id,
            trace_id,
            len(msg) if msg else 0,
            list(final_state.keys()),
        )

        # Log clave: ver qué trae el estado al final del grafo
        logger.info("Final state keys: %s", list(final_state.keys()))
        logger.info("final_sections in state: %s", final_state.get("final_sections"))
        logger.info("generated_at in state: %r", final_state.get("generated_at"))

        # Mapeamos el estado -> contrato de respuesta
        resp = ScanResponse.from_state(final_state)
        logger.info("SCAN END OK client_id=%s trace_id=%s", req.client_id, trace_id)
        return jsonify(resp.model_dump()), 200
    except Exception as e:
        logger.exception("SCAN ERROR")
        tb = traceback.format_exc()

        # Intentar destapar ExceptionGroup / TaskGroup
        inner = None
        if hasattr(e, "exceptions"):  # ExceptionGroup en Py 3.11+
            inner = [repr(ex) for ex in e.exceptions]

        error_payload = {
            "error": str(e),
            "traceback": tb,
        }
        if inner is not None:
            error_payload["inner_exceptions"] = inner

        # IMPORTANTE: dejar esto mientras se depura; luego se puede simplificar
        return jsonify(error_payload), 500

logger.info("== URL MAP ==")
logger.info("%s", app.url_map)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8010)), debug=False, use_reloader=False)
