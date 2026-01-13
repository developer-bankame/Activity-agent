import logging
import requests

logger = logging.getLogger(__name__)

class DBToolClient:
    """
    Cliente HTTP simple para el DB Tool Service (Cloud Run).
    Espera que el endpoint acepte POST {client_id} y devuelva:
      { "ok": true, "result": { "full_name": "...", "employer": "...", ... } }
    """

    def __init__(self, settings):
        self.base_url = settings.DB_TOOL_URL.rstrip("/")
        self.auth_header = settings.DB_TOOL_AUTH
        self.session = requests.Session()
        self.timeout = settings.DB_TOOL_TIMEOUT_SECONDS

    def _headers(self):
        h = {"Content-Type": "application/json"}
        if self.auth_header:
            h["Authorization"] = self.auth_header
        return h

    def get_client_profile(self, client_id: int):
        url = f"{self.base_url}"
        logger.info(
            "DBToolClient.get_client_profile START url=%s client_id=%s timeout=%s",
            url,
            client_id,
            self.timeout,
        )
        resp = self.session.post(
            url,
            json={"client_id": client_id},
            headers=self._headers(),
            timeout=self.timeout,
        )
        logger.info(
            "DBToolClient.get_client_profile RESPONSE status=%s",
            resp.status_code,
        )
        resp.raise_for_status()
        data = resp.json()
        logger.debug("DBToolClient response JSON=%s", data)

        if not data.get("ok"):
            logger.error("DB Tool returned ok=false for client_id=%s", client_id)
            raise RuntimeError("DB Tool returned ok=false")
        
        result = data["result"]
        logger.info(
            "DBToolClient.get_client_profile OK client_id=%s full_name=%s employer=%s",
            client_id,
            result.get("full_name"),
            result.get("employer"),
            result.get("activity_declared"),
        )
        return result
