"""
Stub de test pour `server.common.service`.

Reproduit uniquement le contrat utilisé par `voice/app.py` :
`create_service_app(name, title, version, capabilities, setup, health)` ->
une FastAPI app dont le lifespan appelle `setup(app)` et qui expose un
`GET /health` fusionnant `health(request)` avec les métadonnées du service.

À NE PAS UTILISER EN PRODUCTION — voir tests/conftest.py pour la logique de
priorité entre le vrai `server.common` (s'il est sur le PYTHONPATH) et ce
stub (utilisé seulement en repli, pour tester `voice` de façon isolée).
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Callable

from fastapi import FastAPI, Request


def create_service_app(
    *,
    name: str,
    title: str,
    version: str,
    capabilities: list[str],
    setup: Callable,
    health: Callable[[Any], dict] | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with setup(app):
            yield

    app = FastAPI(title=title, version=version, lifespan=lifespan)

    @app.get("/health")
    async def _health(request: Request) -> dict:
        details = health(request) if health else {}
        return {"service": name, "version": version, "capabilities": capabilities, **details}

    return app
