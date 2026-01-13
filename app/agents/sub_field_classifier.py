# app/agents/sub_field_classifier.py
from google.adk import Agent
from google.genai import types
from app.tools.state_utils import set_state


def make_sub_field_classifier(settings):
    return Agent(
        name="sub_field_classifier",
        model=settings.MODEL,
        description="Classify 'sub_field' conditioned on the already-chosen field.",
        instruction="""
        TASK:
          Choose a 'sub_field' for the already selected field.

        INPUT STATE:
          field: { field? }
          employer: { employer? }
          sector: { sector? }
          activity_declared: { activity_declared? }

          field_to_sub_fields: { field_to_sub_fields? }

        RULES (STRICT):
          - Compute the allowed list:
              allowed = field_to_sub_fields[field]
            If field is missing or allowed is empty or undefined:
              set sub_field = null
          - If allowed has exactly 1 item, choose it.
          - Otherwise, choose EXACTLY one sub_field from allowed.
          - Do NOT invent labels outside allowed.

        OUTPUT:
          Call set_state exactly once:
            set_state(key="sub_field", value=<chosen_sub_field_or_null>)

          Do NOT output free text.
        """,
        tools=[set_state],
        generate_content_config=types.GenerateContentConfig(temperature=0),
    )
