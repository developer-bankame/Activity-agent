import asyncio
import logging

from google.adk.agents import Agent, SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from app.agents.orchestrator import make_orchestrator
from app.agents.field_classifier import make_field_classifier
from app.agents.role_classifier import make_role_classifier

logger = logging.getLogger(__name__)

APP_NAME = "activity_agent"


class GraphRunner:
    def __init__(self, root_agent: Agent, app_name: str = APP_NAME):
        self.root_agent = root_agent
        self.app_name = app_name

    def run(self, state: dict):
        async def _run_async():
            logger.info(
                "GraphRunner._run_async START app_name=%s trace_id=%s client_id=%s",
                self.app_name,
                state.get("trace_id"),
                state.get("client_id"),
            )

            session_service = InMemorySessionService()
            user_id = state.get("trace_id") or "backend-service"

            session = await session_service.create_session(
                app_name=self.app_name,
                user_id=user_id,
                state=state,
            )

            runner = Runner(
                agent=self.root_agent,
                app_name=self.app_name,
                session_service=session_service,
            )

            kickoff_msg = genai_types.Content(
                role="user",
                parts=[
                    genai_types.Part(
                        text=(
                            "START_ACTIVITY. "
                            f"client_id={state.get('client_id')} "
                            f"trace_id={state.get('trace_id')}."
                        )
                    )
                ],
            )

            events = runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=kickoff_msg,
            )

            last_text = ""
            async for event in events:
                if getattr(event, "is_final_response", None) and event.is_final_response():
                    content = getattr(event, "content", None)
                    if content and getattr(content, "parts", None):
                        part = content.parts[0]
                        if getattr(part, "text", None):
                            last_text = part.text

            updated_session = await session_service.get_session(
                app_name=self.app_name,
                user_id=user_id,
                session_id=session.id,
            )

            final_state = dict(updated_session.state or {})
            logger.info("Final state loaded. keys=%s", list(final_state.keys()))
            return last_text, final_state

        return asyncio.run(_run_async())


def build_graph(settings):
    activity_pipeline = SequentialAgent(
        name="activity_pipeline",
        sub_agents=[
            make_orchestrator(settings),      # fetch profile + load taxonomies
            make_field_classifier(settings),  # set_state(field)
            make_role_classifier(settings),   # set_state(role)
        ],
    )

    root = Agent(
        name="root",
        model=settings.MODEL,
        instruction=(
            "You are the root coordinator for an activity classification.\n"
            "- THINK in English.\n"
            "- Do NOT output free text.\n\n"
            "When you receive 'START_ACTIVITY ...', you MUST:\n"
            "1) Transfer control to 'activity_pipeline'.\n"
            "2) Ensure it runs end-to-end:\n"
            "   - orchestrator -> field_classifier -> role_classifier\n"
            "3) Sub-agents will update shared state; response is built from final state.\n"
        ),
        sub_agents=[activity_pipeline],
    )

    return GraphRunner(root_agent=root, app_name=APP_NAME)
