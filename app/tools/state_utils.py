import logging
import time
import random
from typing import Any, Dict, Callable, Iterable, Optional

from google.adk.tools import ToolContext

logger = logging.getLogger(__name__)


def set_state(key: str, value: Any, tool_context: ToolContext) -> dict:
    """
    Tool genérico: guarda cualquier valor en el estado compartido.

    Uso típico en este proyecto:
      - set_state("field", "<label>")
      - set_state("role", "<label>")
      - set_state("tax_fields", [...])
      - set_state("tax_roles", [...])
      - set_state("field_to_roles", {...})
    """
    tool_context.state[key] = value

    # logging liviano
    size = None
    if isinstance(value, (list, dict, str)):
        try:
            size = len(value)
        except Exception:
            size = None

    logger.info("set_state key=%s type=%s size=%s", key, type(value).__name__, size)
    return {"status": "success", "written_key": key, "type": type(value).__name__}


def append_to_state(key: str, value: Any, tool_context: ToolContext) -> dict:
    """
    Tool: agrega 'value' a una lista en el estado (creándola si no existe).
    Útil para debug o métricas, aunque en Activity-agent casi no se usa.
    """
    existing = tool_context.state.get(key)
    if existing is None:
        existing = []
    if not isinstance(existing, list):
        # Si el key existe pero no es lista, lo convertimos a lista
        existing = [existing]

    existing.append(value)
    tool_context.state[key] = existing

    logger.info("append_to_state key=%s new_length=%s", key, len(existing))
    return {"status": "success", "key": key, "new_length": len(existing)}


def retry_with_backoff(
    max_attempts: int = 3,
    base_backoff: float = 0.5,
    max_backoff: float = 8.0,
    jitter: float = 0.2,
    retry_exceptions: Iterable[type] = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None,
):
    """
    Decorator: retries con exponential backoff + jitter.
    Útil si tu DBToolClient o llamadas externas fallan por intermitencia.
    """
    def decorator(fn):
        def wrapper(*args, **kwargs):
            attempt = 1
            while True:
                try:
                    return fn(*args, **kwargs)
                except tuple(retry_exceptions) as exc:
                    if attempt >= max_attempts:
                        logger.debug("Retries exhausted (%d) for %s", attempt, getattr(fn, "__name__", str(fn)))
                        raise

                    if on_retry:
                        try:
                            on_retry(attempt, exc)
                        except Exception:
                            logger.exception("on_retry handler failed")

                    sleep_base = min(max_backoff, base_backoff * (2 ** (attempt - 1)))
                    sleep = sleep_base * (1 + random.uniform(-jitter, jitter))
                    logger.warning(
                        "Retry attempt %d/%d for %s: %s — sleeping %.2fs",
                        attempt, max_attempts, getattr(fn, "__name__", str(fn)), exc, sleep
                    )
                    time.sleep(sleep)
                    attempt += 1
        return wrapper
    return decorator
