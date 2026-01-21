import logging
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


class Inputs(BaseModel):
    employer: Optional[str] = None
    sector: Optional[str] = None
    activity_declared: Optional[str] = None


class ScanResponse(BaseModel):
    client_id: int
    generated_at: str

    # Inputs (lo que vino del DB Tool Service)
    inputs: Inputs

    # Outputs (lo que clasifica el agent)
    field: str
    role: str


    @classmethod
    def from_state(cls, s: Dict[str, Any], *, include_debug: bool = False):
        """
        Mapea el estado final del grafo a nuestro contrato de salida.
        Se asume que el pipeline dejó:
          - client_id
          - employer, sector, activity_declared
          - field, role
          - generated_at (opcional)
        """
        logger.info("ActivityResponse.from_state called")
        logger.info("State keys: %s", list(s.keys()))

        # Fallback generated_at (America/La_Paz ~= UTC-4)
        generated_at = s.get("generated_at")
        if not generated_at:
            tz = timezone(timedelta(hours=-4))
            generated_at = datetime.now(tz).isoformat()

        # Outputs obligatorios con fallback seguro
        field = s.get("field") or "Indefinido"
        role = s.get("role") or "No definido"

        payload = {
            "client_id": s["client_id"],
            "generated_at": generated_at,
            "inputs": {
                "employer": s.get("employer"),
                "sector": s.get("sector"),
                "activity_declared": s.get("activity_declared"),
            },
            "field": field,
            "role": role,
        }

        return cls(**payload)
