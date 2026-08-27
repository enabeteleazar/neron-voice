"""
Stub de test pour `agents.builtin.base_agent`.

Reproduit uniquement le contrat utilisé par `voice/adapters/legacy_agents.py` :
la dataclass `AgentResult` (success, content, source, error, latency_ms,
metadata) et `get_logger(name)`.

À NE PAS UTILISER EN PRODUCTION — si le vrai module `agents.builtin.base_agent`
diverge de ce contrat, ces tests ne le détecteront pas. Il vaut la peine de
comparer périodiquement ce stub à l'implémentation réelle du monorepo.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    success: bool
    content: str
    source: str
    error: str | None = None
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
