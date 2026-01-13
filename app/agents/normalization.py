# app/agents/normalization.py
from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict

_WS_RE = re.compile(r"\s+")


def strip_accents(text: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(ch)
    )


def normalize_text(text: str | None) -> str:
    """
    Normalización determinística para señales de texto.
    - None -> ""
    - trim
    - colapsa espacios
    - lower
    - quita tildes
    """
    if not text:
        return ""
    s = str(text).strip()
    s = _WS_RE.sub(" ", s)
    s = strip_accents(s)
    return s.lower()


def normalize_profile(profile: Dict[str, Any]) -> Dict[str, str]:
    """
    Espera keys (si existen):
      - employer
      - sector
      - activity_declared
    Devuelve versión normalizada.
    """
    return {
        "employer_norm": normalize_text(profile.get("employer")),
        "sector_norm": normalize_text(profile.get("sector")),
        "activity_declared_norm": normalize_text(profile.get("activity_declared")),
    }
