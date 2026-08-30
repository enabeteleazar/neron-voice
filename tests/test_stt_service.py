from __future__ import annotations

import asyncio
import os
import time

import pytest

import voice.stt.service as stt_service
from voice.models import TranscriptionResult
from voice.stt.providers.base import SttProvider


class FakeSttProvider(SttProvider):
    """Provider de test : pas de modèle réel, comportement contrôlable."""

    def __init__(self, delay: float = 0.0, text: str = "bonjour", ready: bool = True):
        self.delay = delay
        self.text = text
        self._ready = ready
        self.seen_paths: list[str] = []

    def load(self) -> object:
        self._ready = True
        return self

    def is_ready(self) -> bool:
        return self._ready

    def transcribe_file(self, path: str) -> TranscriptionResult:
        self.seen_paths.append(path)
        if self.delay:
            time.sleep(self.delay)
        return TranscriptionResult(text=self.text, language="fr", confidence=None, metadata={})


def _make_wav_bytes() -> bytes:
    return b"RIFF....WAVEfmt fake-not-a-real-wav-but-bytes-are-enough"


@pytest.mark.asyncio
async def test_transcribe_raises_if_provider_not_loaded(clean_env):
    stt_service._provider = None
    with pytest.raises(RuntimeError, match="non chargé"):
        await stt_service.transcribe(_make_wav_bytes(), "clip.wav")


@pytest.mark.asyncio
async def test_transcribe_raises_if_provider_not_ready(clean_env):
    stt_service._provider = FakeSttProvider(ready=False)
    with pytest.raises(RuntimeError, match="non chargé"):
        await stt_service.transcribe(_make_wav_bytes(), "clip.wav")


@pytest.mark.asyncio
async def test_validation_error_raised_before_touching_provider(clean_env):
    provider = FakeSttProvider()
    stt_service._provider = provider
    with pytest.raises(ValueError):
        await stt_service.transcribe(_make_wav_bytes(), "clip.aiff")
    assert provider.seen_paths == []  # jamais appelé : la validation a bloqué avant


@pytest.mark.asyncio
async def test_successful_transcription_returns_expected_result(clean_env):
    stt_service._provider = FakeSttProvider(text="bonjour néron")
    result = await stt_service.transcribe(_make_wav_bytes(), "clip.wav")
    assert result.text == "bonjour néron"
    assert result.language == "fr"
    assert "duration_ms" in result.metadata


@pytest.mark.asyncio
async def test_temp_file_is_cleaned_up_after_transcription(clean_env):
    provider = FakeSttProvider()
    stt_service._provider = provider
    await stt_service.transcribe(_make_wav_bytes(), "clip.wav")
    assert len(provider.seen_paths) == 1
    assert not os.path.exists(provider.seen_paths[0]), "le fichier temporaire aurait dû être supprimé"


@pytest.mark.asyncio
async def test_check_connection_reflects_provider_state(clean_env):
    assert stt_service.check_connection() is False
    stt_service._provider = FakeSttProvider(ready=False)
    assert stt_service.check_connection() is False
    stt_service._provider.load()
    assert stt_service.check_connection() is True


@pytest.mark.asyncio
async def test_transcribe_times_out_on_slow_provider(clean_env, monkeypatch):
    """
    Régression P0 : sans timeout, un provider bloqué faisait pendre la
    requête indéfiniment. On force `config.timeout` très bas et on vérifie
    qu'on récupère un TimeoutError rapidement plutôt que d'attendre le
    provider (qui dort volontairement plus longtemps que le timeout).
    """
    from voice.config.loader import SttConfig, TtsConfig, LanguageConfig, VoiceConfig

    short_timeout_config = VoiceConfig(
        stt=SttConfig(timeout=1),
        tts=TtsConfig(),
        language=LanguageConfig(),
    )
    monkeypatch.setattr(stt_service, "load_voice_config", lambda: short_timeout_config)

    stt_service._provider = FakeSttProvider(delay=5.0)

    start = time.monotonic()
    with pytest.raises(TimeoutError, match="timeout"):
        await stt_service.transcribe(_make_wav_bytes(), "clip.wav")
    elapsed = time.monotonic() - start

    assert elapsed < 3.0, "le timeout aurait dû couper bien avant les 5s du provider"


@pytest.mark.asyncio
async def test_transcribe_completes_normally_within_timeout(clean_env, monkeypatch):
    from voice.config.loader import SttConfig, TtsConfig, LanguageConfig, VoiceConfig

    generous_timeout_config = VoiceConfig(
        stt=SttConfig(timeout=5),
        tts=TtsConfig(),
        language=LanguageConfig(),
    )
    monkeypatch.setattr(stt_service, "load_voice_config", lambda: generous_timeout_config)
    stt_service._provider = FakeSttProvider(delay=0.05, text="ça marche")

    result = await stt_service.transcribe(_make_wav_bytes(), "clip.wav")
    assert result.text == "ça marche"


def test_build_provider_rejects_unsupported_provider(clean_env, monkeypatch):
    from voice.config.loader import SttConfig, TtsConfig, LanguageConfig, VoiceConfig

    monkeypatch.setattr(
        stt_service,
        "load_voice_config",
        lambda: VoiceConfig(stt=SttConfig(provider="vosk"), tts=TtsConfig(), language=LanguageConfig()),
    )
    with pytest.raises(RuntimeError, match="non supporté"):
        stt_service._build_provider()
