from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

from voice.config import load_voice_config
from voice.models import TranscriptionResult
from voice.stt.pipeline import validate_audio_input
from voice.stt.providers import FasterWhisperProvider
from voice.stt.providers.base import SttProvider

logger = logging.getLogger("voice.stt")

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="voice_stt")
_provider: SttProvider | None = None


def _build_provider() -> SttProvider:
    config = load_voice_config().stt
    if config.provider != "whisper":
        raise RuntimeError(f"Provider STT non supporté : {config.provider}")
    return FasterWhisperProvider(config)


def load_model() -> object:
    global _provider
    _provider = _build_provider()
    return _provider.load()


def check_connection() -> bool:
    return _provider is not None and _provider.is_ready()


async def transcribe(audio: bytes, filename: str = "audio.wav") -> TranscriptionResult:
    config = load_voice_config().stt
    ext = validate_audio_input(audio, filename, config.max_size_mb)
    if _provider is None or not _provider.is_ready():
        raise RuntimeError("Modèle STT non chargé")

    loop = asyncio.get_event_loop()
    future = loop.run_in_executor(_executor, _transcribe_sync, audio, ext)

    # On utilise asyncio.wait() plutôt que asyncio.wait_for() ici : wait_for
    # tente d'annuler le Future à l'expiration du délai, mais l'annulation
    # d'un Future d'executor déjà en cours d'exécution est documentée comme
    # sans effet ET comme un point de comportement qui a varié entre
    # versions de Python (perte de l'annulation, ou attente de la
    # complétion malgré tout selon la version). asyncio.wait() n'essaie
    # jamais d'annuler : il attend juste le délai, puis nous laissons le
    # Future pending tel quel — comportement simple et stable, quelle que
    # soit la version de Python.
    done, pending = await asyncio.wait({future}, timeout=config.timeout)

    if future in pending:
        # NB : le thread du ThreadPoolExecutor continue de tourner en
        # arrière-plan jusqu'à ce que faster-whisper rende la main (il n'y a
        # pas d'annulation dure possible pour un appel bloquant en thread
        # natif). Ça protège la requête HTTP d'un blocage infini, mais pas
        # le pool lui-même contre un worker durablement occupé — un vrai
        # correctif (process isolé, ou timeout côté modèle) reste à faire
        # si ça se produit souvent.
        logger.error(
            "Timeout STT après %ss (%s, %d octets) — le worker continue en arrière-plan.",
            config.timeout, ext, len(audio),
        )
        raise TimeoutError(f"Transcription STT au-delà du timeout ({config.timeout}s)")

    return future.result()


def _transcribe_sync(audio: bytes, ext: str) -> TranscriptionResult:
    start = time.monotonic()
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(audio)
            tmp_path = tmp.name
        assert _provider is not None
        result = _provider.transcribe_file(tmp_path)
        metadata = dict(result.metadata)
        metadata.setdefault("duration_ms", round((time.monotonic() - start) * 1000, 2))
        logger.info(
            "STT %s : %d octets, %s ms, texte %d car. : %r",
            ext, len(audio), metadata.get("duration_ms"), len(result.text), result.text[:120],
        )
        return TranscriptionResult(
            text=result.text,
            language=result.language,
            confidence=result.confidence,
            metadata=metadata,
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
