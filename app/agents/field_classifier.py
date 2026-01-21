# app/agents/field_classifier.py
from google.adk import Agent
from google.genai import types
from app.tools.state_utils import set_state


def make_field_classifier(settings):
    return Agent(
        name="field_classifier",
        model=settings.MODEL,
        description="Classify 'field' (rubro/industria) from employer/sector/activity_declared using a closed taxonomy.",
        instruction="""
        TASK:
          Choose EXACTLY one 'field' from the allowed taxonomy list.

        INPUT STATE:
          employer: { employer? }
          sector: { sector? }
          activity_declared: { activity_declared? }
          employer_norm: { employer_norm? }
          sector_norm: { sector_norm? }
          activity_declared_norm: { activity_declared_norm? }

          tax_fields: { tax_fields? }

        RULES (STRICT):
          - You MUST choose one value that is EXACTLY in `tax_fields`.
          - Do NOT invent new labels.
          - Heuristic:
              * If `sector_norm` matches a value in `tax_fields` and it is NOT "otros",
                then choose that as field.
              * Otherwise, infer using employer/activity_declared.

        OUTPUT:
          Call set_state exactly once:
            set_state(key="field", value="<chosen_field>")

          Do NOT output free text.
        """,
        tools=[set_state],
        generate_content_config=types.GenerateContentConfig(temperature=0),
    )
