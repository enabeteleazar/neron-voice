from __future__ import annotations

import base64
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import voice.app as app_module
from agents.builtin.base_agent import AgentResult


@pytest.fixture
def client(monkeypatch):
    # On évite tout chargement réel de modèle (réseau, fichiers de voix
    # absents, etc.) : ce n'est pas l'objet de ces tests, et ça les rendrait
    # lents/instables. Le comportement de dégradation gracieuse lui-même
    # (_setup qui n'échoue pas si le chargement rate) est couvert ailleurs
    # implicitement, puisque stt_agent/tts_agent restent non None malgré
    # l'échec de chargement.
    monkeypatch.setattr(app_module, "load_stt_model", lambda: None)
    monkeypatch.setattr(app_module, "load_tts_engine", lambda: None)

    with TestClient(app_module.app) as test_client:
        yield test_client


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def test_startup_degrades_gracefully_when_stt_load_fails(monkeypatch):
    """
    Propriété de conception à verrouiller : un échec de chargement au
    démarrage (STT ou TTS) ne doit jamais empêcher le service de démarrer
    (pas de crash-loop). stt_agent doit rester défini, /health doit juste
    remonter "not ready".
    """

    def boom():
        raise RuntimeError("modèle introuvable sur le disque")

    monkeypatch.setattr(app_module, "load_stt_model", boom)
    monkeypatch.setattr(app_module, "load_tts_engine", lambda: None)

    with TestClient(app_module.app) as test_client:
        assert app_module.stt_agent is not None
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json()["stt_ready"] is False


def test_health_endpoint_reports_not_ready_without_loaded_models(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["stt_ready"] is False
    assert body["tts_ready"] is False


def test_transcribe_returns_503_when_stt_agent_missing(client, monkeypatch):
    monkeypatch.setattr(app_module, "stt_agent", None)
    response = client.post("/transcribe", json={"audio_b64": _b64(b"x"), "filename": "clip.wav"})
    assert response.status_code == 503


def test_transcribe_returns_400_on_invalid_base64(client):
    response = client.post("/transcribe", json={"audio_b64": "%%%not-base64%%%", "filename": "clip.wav"})
    assert response.status_code == 400


def test_transcribe_returns_400_on_validation_error(client, monkeypatch):
    async def fake_transcribe(audio_bytes, filename):
        return AgentResult(
            success=False,
            content="",
            source="stt_agent",
            error="Format non supporté : '.aiff'",
            latency_ms=1.0,
            metadata={"error_type": "validation"},
        )

    monkeypatch.setattr(app_module.stt_agent, "transcribe", fake_transcribe)
    response = client.post("/transcribe", json={"audio_b64": _b64(b"x"), "filename": "clip.aiff"})
    assert response.status_code == 400
    assert "non supporté" in response.json()["detail"]


def test_transcribe_returns_504_on_timeout(client, monkeypatch):
    async def fake_transcribe(audio_bytes, filename):
        return AgentResult(
            success=False,
            content="",
            source="stt_agent",
            error="Transcription STT au-delà du timeout (60s)",
            latency_ms=60_000.0,
            metadata={"error_type": "timeout"},
        )

    monkeypatch.setattr(app_module.stt_agent, "transcribe", fake_transcribe)
    response = client.post("/transcribe", json={"audio_b64": _b64(b"x"), "filename": "clip.wav"})
    assert response.status_code == 504


def test_transcribe_returns_422_on_internal_error(client, monkeypatch):
    async def fake_transcribe(audio_bytes, filename):
        return AgentResult(
            success=False,
            content="",
            source="stt_agent",
            error="Modèle STT non chargé",
            latency_ms=1.0,
            metadata={"error_type": "internal"},
        )

    monkeypatch.setattr(app_module.stt_agent, "transcribe", fake_transcribe)
    response = client.post("/transcribe", json={"audio_b64": _b64(b"x"), "filename": "clip.wav"})
    assert response.status_code == 422


def test_transcribe_returns_422_by_default_without_error_type(client, monkeypatch):
    """Filet de sécurité : un futur error_type non mappé ne doit pas
    remonter en 200, il doit tomber sur le défaut 422 plutôt que planter."""

    async def fake_transcribe(audio_bytes, filename):
        return AgentResult(
            success=False, content="", source="stt_agent", error="???", latency_ms=1.0, metadata={},
        )

    monkeypatch.setattr(app_module.stt_agent, "transcribe", fake_transcribe)
    response = client.post("/transcribe", json={"audio_b64": _b64(b"x"), "filename": "clip.wav"})
    assert response.status_code == 422


def test_transcribe_success_returns_200_with_text(client, monkeypatch):
    async def fake_transcribe(audio_bytes, filename):
        return AgentResult(
            success=True,
            content="bonjour néron",
            source="stt_agent",
            error=None,
            latency_ms=42.0,
            metadata={"language": "fr", "confidence": None},
        )

    monkeypatch.setattr(app_module.stt_agent, "transcribe", fake_transcribe)
    response = client.post("/transcribe", json={"audio_b64": _b64(b"x"), "filename": "clip.wav"})
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["text"] == "bonjour néron"
    assert body["language"] == "fr"


def test_synthesize_returns_503_when_tts_agent_missing(client, monkeypatch):
    monkeypatch.setattr(app_module, "tts_agent", None)
    response = client.post("/synthesize", json={"text": "Bonjour"})
    assert response.status_code == 503


def test_synthesize_returns_422_on_failure(client, monkeypatch):
    async def fake_synthesize(text):
        return AgentResult(
            success=False, content="", source="tts_agent", error="Texte vide", latency_ms=1.0, metadata={},
        )

    monkeypatch.setattr(app_module.tts_agent, "synthesize", fake_synthesize)
    response = client.post("/synthesize", json={"text": "Bonjour"})
    assert response.status_code == 422


def test_synthesize_success_returns_audio_bytes(client, monkeypatch):
    async def fake_synthesize(text):
        return AgentResult(
            success=True,
            content="",
            source="tts_agent",
            error=None,
            latency_ms=10.0,
            metadata={"audio_bytes": b"fake-mp3-bytes", "mimetype": "audio/mpeg"},
        )

    monkeypatch.setattr(app_module.tts_agent, "synthesize", fake_synthesize)
    response = client.post("/synthesize", json={"text": "Bonjour"})
    assert response.status_code == 200
    assert response.content == b"fake-mp3-bytes"
    assert response.headers["content-type"] == "audio/mpeg"


def test_synthesize_rejects_empty_text_via_pydantic(client):
    response = client.post("/synthesize", json={"text": ""})
    assert response.status_code == 422  # min_length=1 -> erreur de validation FastAPI


def test_reload_endpoint_reports_both_results(client, monkeypatch):
    async def fake_stt_reload():
        return True

    async def fake_tts_reload():
        return False

    monkeypatch.setattr(app_module.stt_agent, "reload", fake_stt_reload)
    monkeypatch.setattr(app_module.tts_agent, "reload", fake_tts_reload)

    response = client.post("/reload")
    assert response.status_code == 200
    assert response.json() == {"stt_reloaded": True, "tts_reloaded": False}


def test_reload_endpoint_handles_missing_agents(client, monkeypatch):
    monkeypatch.setattr(app_module, "stt_agent", None)
    monkeypatch.setattr(app_module, "tts_agent", None)

    response = client.post("/reload")
    assert response.status_code == 200
    assert response.json() == {"stt_reloaded": False, "tts_reloaded": False}


def test_transcribe_rejects_unknown_extra_fields(client):
    # TranscribeRequest a model_config extra="forbid"
    response = client.post(
        "/transcribe",
        json={"audio_b64": _b64(b"x"), "filename": "clip.wav", "unexpected": "field"},
    )
    assert response.status_code == 422


def test_transcribe_rejects_empty_audio_b64(client):
    response = client.post("/transcribe", json={"audio_b64": "", "filename": "clip.wav"})
    assert response.status_code == 422
