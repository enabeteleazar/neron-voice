from __future__ import annotations

import pytest

import voice.stt as stt
import voice.tts as tts
from voice.adapters.legacy_agents import STTAgent, TTSAgent
from voice.models import SpeechResult, TranscriptionResult


@pytest.mark.asyncio
async def test_stt_agent_success_path(monkeypatch):
    async def fake_transcribe(audio, filename):
        return TranscriptionResult(text="bonjour", language="fr", confidence=None, metadata={"duration_ms": 12.0})

    monkeypatch.setattr(stt, "transcribe", fake_transcribe)
    agent = STTAgent()
    result = await agent.transcribe(b"audio", "clip.wav")

    assert result.success is True
    assert result.content == "bonjour"
    assert result.metadata["language"] == "fr"
    assert result.error is None


@pytest.mark.asyncio
async def test_stt_agent_validation_error_is_tagged(monkeypatch):
    async def fake_transcribe(audio, filename):
        raise ValueError("Format non supporté : '.aiff'")

    monkeypatch.setattr(stt, "transcribe", fake_transcribe)
    agent = STTAgent()
    result = await agent.transcribe(b"audio", "clip.aiff")

    assert result.success is False
    assert result.metadata["error_type"] == "validation"
    assert "non supporté" in result.error


@pytest.mark.asyncio
async def test_stt_agent_timeout_is_tagged(monkeypatch):
    async def fake_transcribe(audio, filename):
        raise TimeoutError("Transcription STT au-delà du timeout (60s)")

    monkeypatch.setattr(stt, "transcribe", fake_transcribe)
    agent = STTAgent()
    result = await agent.transcribe(b"audio", "clip.wav")

    assert result.success is False
    assert result.metadata["error_type"] == "timeout"


@pytest.mark.asyncio
async def test_stt_agent_unexpected_error_is_tagged_internal(monkeypatch):
    async def fake_transcribe(audio, filename):
        raise RuntimeError("Modèle STT non chargé")

    monkeypatch.setattr(stt, "transcribe", fake_transcribe)
    agent = STTAgent()
    result = await agent.transcribe(b"audio", "clip.wav")

    assert result.success is False
    assert result.metadata["error_type"] == "internal"


@pytest.mark.asyncio
async def test_tts_agent_success_path(monkeypatch):
    async def fake_speak(text, options=None):
        return SpeechResult(audio=b"bytes", format="mp3", metadata={"latency_ms": 5.0})

    monkeypatch.setattr(tts, "speak", fake_speak)
    agent = TTSAgent()
    result = await agent.synthesize("Bonjour")

    assert result.success is True
    assert result.metadata["audio_bytes"] == b"bytes"
    assert result.metadata["format"] == "mp3"


@pytest.mark.asyncio
async def test_tts_agent_any_error_reports_failure(monkeypatch):
    """
    TTSAgent distingue désormais les types d'erreur (validation vs interne)
    comme STTAgent.
    """
    async def fake_speak(text, options=None):
        raise ValueError("Texte vide")

    monkeypatch.setattr(tts, "speak", fake_speak)
    agent = TTSAgent()
    result = await agent.synthesize("")

    assert result.success is False
    assert result.metadata["error_type"] == "validation"
    assert "Texte vide" in result.error


@pytest.mark.asyncio
async def test_stt_agent_reload_success(monkeypatch):
    monkeypatch.setattr(stt, "load_model", lambda: object())
    agent = STTAgent()
    assert await agent.reload() is True


@pytest.mark.asyncio
async def test_stt_agent_reload_failure_is_swallowed(monkeypatch):
    def boom():
        raise RuntimeError("modèle introuvable")

    monkeypatch.setattr(stt, "load_model", boom)
    agent = STTAgent()
    assert await agent.reload() is False


@pytest.mark.asyncio
async def test_stt_agent_check_connection_delegates_to_module(monkeypatch):
    monkeypatch.setattr(stt, "check_connection", lambda: True)
    agent = STTAgent()
    assert await agent.check_connection() is True


@pytest.mark.asyncio
async def test_tts_agent_reload_success(monkeypatch):
    monkeypatch.setattr(tts, "load_engine", lambda: object())
    agent = TTSAgent()
    assert await agent.reload() is True


@pytest.mark.asyncio
async def test_tts_agent_reload_failure_is_swallowed(monkeypatch):
    def boom():
        raise RuntimeError("voix introuvable")

    monkeypatch.setattr(tts, "load_engine", boom)
    agent = TTSAgent()
    assert await agent.reload() is False


@pytest.mark.asyncio
async def test_tts_agent_check_connection_delegates_to_module(monkeypatch):
    monkeypatch.setattr(tts, "check_connection", lambda: False)
    agent = TTSAgent()
    assert await agent.check_connection() is False
