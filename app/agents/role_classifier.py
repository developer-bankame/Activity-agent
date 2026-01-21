# app/agents/role_classifier.py
import logging
from google.adk import Agent
from google.genai import types
from app.tools.state_utils import set_state

logger = logging.getLogger(__name__)


def make_role_classifier(settings):
    def prepare_allowed_roles(tool_context):
        """
        Tool: calcula roles permitidos a partir de:
          - field_sub_to_roles (map con key "field||sub_field")
          - field_to_roles (map por field)
          - tax_roles (fallback)
        y lo guarda en state['allowed_roles'].
        """
        field = tool_context.state.get("field")
        sub_field = tool_context.state.get("sub_field")

        field_sub_to_roles = tool_context.state.get("field_sub_to_roles") or {}
        field_to_roles = tool_context.state.get("field_to_roles") or {}
        tax_roles = tool_context.state.get("tax_roles") or []

        allowed = None

        if field and sub_field:
            key = f"{field}||{sub_field}"
            if key in field_sub_to_roles:
                allowed = field_sub_to_roles.get(key)

        if allowed is None and field and field in field_to_roles:
            allowed = field_to_roles.get(field)

        if not allowed:
            allowed = tax_roles

        tool_context.state["allowed_roles"] = allowed
        logger.info("prepare_allowed_roles field=%s sub_field=%s allowed_roles=%s", field, sub_field, allowed)
        return {"status": "success", "allowed_roles_count": len(allowed)}

    return Agent(
        name="role_classifier",
        model=settings.MODEL,
        description="Classify 'role' conditioned on field/sub_field with a closed allowed-role list.",
        instruction="""
        TASK:
          Choose EXACTLY one 'role' from the allowed roles for this (field, sub_field).

        STEPS:
          1) Call `prepare_allowed_roles` once.
          2) Choose EXACTLY one role from `allowed_roles`.

        INPUT STATE:
          field: { field? }
          sub_field: { sub_field? }
          employer: { employer? }
          sector: { sector? }
          activity_declared: { activity_declared? }

          allowed_roles: { allowed_roles? }
          tax_roles: { tax_roles? }

        RULES (STRICT):
          - You MUST pick a role that is EXACTLY in `allowed_roles`.
          - Do NOT invent labels.
          - Prioritize activity_declared to infer the role; employer/sector are secondary signals.

        OUTPUT:
          Call set_state exactly once:
            set_state(key="role", value="<chosen_role>")

          Do NOT output free text.
        """,
        tools=[prepare_allowed_roles, set_state],
        generate_content_config=types.GenerateContentConfig(temperature=0),
    )
