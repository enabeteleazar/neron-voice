from __future__ import annotations

import pytest

import voice.tts.service as tts_service
from voice.models import SpeechResult
from voice.tts.providers.base import TtsProvider


class FakeTtsProvider(TtsProvider):
    def __init__(self, audio: bytes = b"fake-audio-bytes"):
        self.audio = audio
        self.calls: list[tuple[str, str]] = []

    def name(self) -> str:
        return "fake-tts"

    def synthesize(self, text: str, fmt: str = "mp3") -> SpeechResult:
        self.calls.append((text, fmt))
        return SpeechResult(audio=self.audio, format=fmt, metadata={"engine": self.name()})


@pytest.mark.asyncio
async def test_speak_raises_if_engine_not_loaded(clean_env):
    tts_service._provider = None
    with pytest.raises(RuntimeError, match="non chargé"):
        await tts_service.speak("Bonjour")


@pytest.mark.asyncio
async def test_validation_error_raised_before_touching_provider(clean_env):
    provider = FakeTtsProvider()
    tts_service._provider = provider
    with pytest.raises(ValueError, match="vide"):
        await tts_service.speak("   ")
    assert provider.calls == []


@pytest.mark.asyncio
async def test_speak_uses_configured_format_by_default(clean_env):
    provider = FakeTtsProvider()
    tts_service._provider = provider
    result = await tts_service.speak("Bonjour Néron")
    assert provider.calls[0][1] == "mp3"  # format par défaut de TtsConfig
    assert result.format == "mp3"


@pytest.mark.asyncio
async def test_speak_honors_explicit_format_override(clean_env):
    provider = FakeTtsProvider()
    tts_service._provider = provider
    result = await tts_service.speak("Bonjour", options={"format": "wav"})
    assert provider.calls[0][1] == "wav"
    assert result.format == "wav"


@pytest.mark.asyncio
async def test_speak_enriches_metadata_with_chars_and_latency(clean_env):
    provider = FakeTtsProvider()
    tts_service._provider = provider
    result = await tts_service.speak("Bonjour")
    assert result.metadata["chars"] == len("Bonjour")
    assert "latency_ms" in result.metadata
    assert result.metadata["engine"] == "fake-tts"


@pytest.mark.asyncio
async def test_speak_text_is_normalized_before_counting_chars(clean_env):
    provider = FakeTtsProvider()
    tts_service._provider = provider
    result = await tts_service.speak("   Bonjour   ")
    # validate_tts_text strip le texte -> chars doit compter le texte strippé
    assert result.metadata["chars"] == len("Bonjour")


def test_check_connection_reflects_provider_presence(clean_env):
    tts_service._provider = None
    assert tts_service.check_connection() is False
    tts_service._provider = FakeTtsProvider()
    assert tts_service.check_connection() is True


def test_load_engine_rejects_unsupported_provider(clean_env, monkeypatch):
    from voice.config.loader import SttConfig, TtsConfig, LanguageConfig, VoiceConfig

    monkeypatch.setattr(
        tts_service,
        "load_voice_config",
        lambda: VoiceConfig(stt=SttConfig(), tts=TtsConfig(provider="coqui"), language=LanguageConfig()),
    )
    with pytest.raises(RuntimeError, match="non supporté"):
        tts_service.load_engine()
