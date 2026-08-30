from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("voice.config")


@dataclass(frozen=True)
class SttConfig:
    provider: str = "whisper"
    model: str = "base"
    language: str | None = "fr"
    timeout: int = 60
    max_size_mb: int = 10
    download_root: str = "/etc/neronOS/data/models"


@dataclass(frozen=True)
class TtsConfig:
    provider: str = "piper"
    voice: str = "fr_FR-siwis-medium"
    format: str = "mp3"
    max_chars: int = 1000


@dataclass(frozen=True)
class LanguageConfig:
    default: str = "fr-FR"


@dataclass(frozen=True)
class VoiceConfig:
    stt: SttConfig = SttConfig()
    tts: TtsConfig = TtsConfig()
    language: LanguageConfig = LanguageConfig()


def _project_root() -> Path:
    # server/voice/config/loader.py -> parents[3] == racine du repo (/etc/neronOS).
    # Un VOICE_PROJECT_ROOT explicite permet de bypasser ce calcul si la
    # structure de déploiement change (ou pour les tests).
    override = os.getenv("VOICE_PROJECT_ROOT")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[3]


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        logger.warning("Fichier de config introuvable, defaults utilisés : %s", path)
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        logger.warning("Contenu YAML invalide (pas un mapping), defaults utilisés : %s", path)
        return {}
    return data


def load_voice_config(path: str | Path | None = None) -> VoiceConfig:
    resolved_path = Path(path) if path else _project_root() / "config" / "voice.yaml"
    logger.debug("Chargement config voice depuis : %s", resolved_path)
    raw = _read_yaml(resolved_path)
    stt = raw.get("stt") or {}
    tts = raw.get("tts") or {}
    language = raw.get("language") or {}

    return VoiceConfig(
        stt=SttConfig(
            provider=str(os.getenv("VOICE_STT_PROVIDER", stt.get("provider", "whisper"))),
            model=str(os.getenv("WHISPER_MODEL", stt.get("model", "base"))),
            language=os.getenv("WHISPER_LANGUAGE", stt.get("language", "fr")),
            timeout=int(os.getenv("STT_TIMEOUT", stt.get("timeout", 60))),
            max_size_mb=int(os.getenv("AUDIO_MAX_SIZE_MB", stt.get("max_size_mb", 10))),
            download_root=str(
                os.getenv("WHISPER_DOWNLOAD_ROOT", stt.get("download_root", "/etc/neronOS/data/models"))
            ),
        ),
        tts=TtsConfig(
            provider=str(os.getenv("VOICE_TTS_PROVIDER", tts.get("provider", "piper"))),
            voice=str(os.getenv("TTS_VOICE", tts.get("voice", "fr_FR-siwis-medium"))),
            format=str(os.getenv("TTS_FORMAT", tts.get("format", "mp3"))),
            max_chars=int(os.getenv("TTS_MAX_CHARS", tts.get("max_chars", 1000))),
        ),
        language=LanguageConfig(
            default=str(os.getenv("VOICE_LANGUAGE", language.get("default", "fr-FR"))),
        ),
    )
