# app/agents/orchestrator.py
import logging
from pathlib import Path
from typing import Any, Dict

import yaml
from google.adk import Agent
from google.genai import types

from app.tools.db_tool_client import DBToolClient
from app.tools.state_utils import set_state
from app.agents.normalization import normalize_profile

logger = logging.getLogger(__name__)


def make_orchestrator(settings):
    client = DBToolClient(settings)

    def fetch_profile(tool_context, client_id: int):
        """
        Tool: llama al DB Tool Service y guarda señales en estado.
        Esperamos: employer, sector, activity_declared.
        """
        logger.info("fetch_profile START client_id=%s", client_id)
        profile = client.get_client_profile(client_id)

        # Guarda inputs “raw”
        tool_context.state["client_id"] = client_id
        tool_context.state["employer"] = profile.get("employer")
        tool_context.state["sector"] = profile.get("sector")
        tool_context.state["activity_declared"] = profile.get("activity_declared")

        # Normalizados (útiles para heurísticas o matching exacto)
        tool_context.state.update(normalize_profile(profile))

        logger.info(
            "fetch_profile DONE employer=%s sector=%s activity_declared=%s",
            tool_context.state.get("employer"),
            tool_context.state.get("sector"),
            tool_context.state.get("activity_declared"),
        )
        return {"status": "success"}

    def load_taxonomies(tool_context):
        """
        Tool: carga taxonomías desde config/taxonomies/*.yaml y las guarda en state.
        """
        base_dir = Path(getattr(settings, "TAXONOMIES_DIR", "config/taxonomies"))

        def _read_yaml(name: str) -> Dict[str, Any]:
            p = base_dir / name
            if not p.exists():
                return {}
            with p.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}

        fields_y = _read_yaml("fields.yaml")
        roles_y = _read_yaml("roles.yaml")

        tool_context.state["tax_fields"] = fields_y.get("fields", []) or []
        tool_context.state["tax_roles"] = roles_y.get("roles", []) or []

        # inicializa salidas (útil para debugging / consistencia)
        tool_context.state.setdefault("field", None)
        tool_context.state.setdefault("role", None)

        logger.info(
            "load_taxonomies DONE fields=%d sub_fields=%d roles=%d",
            len(tool_context.state["tax_fields"]),
            len(tool_context.state["tax_roles"]),
        )
        return {"status": "success"}

    return Agent(
        name="orchestrator",
        model=settings.MODEL,
        description="Load client profile and taxonomies to prepare field/sub_field/role classification.",
        instruction="""
        STEPS:
          1) Call `fetch_profile` with { client_id } to load:
             employer, sector, activity_declared, and normalized variants into state.
          2) Call `load_taxonomies` once to load:
             tax_fields, tax_roles.
          3) Do NOT output free text. Finish after tools.

        INPUT:
          client_id: { client_id }
        """,
        tools=[fetch_profile, load_taxonomies, set_state],
        generate_content_config=types.GenerateContentConfig(temperature=0),
    )
