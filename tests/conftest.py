from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
MODULE_DIR = TESTS_DIR.parent          # .../server/voice
SERVER_DIR = MODULE_DIR.parent         # .../server  -> permet `import voice`
STUBS_DIR = TESTS_DIR / "stubs"        # repli pour `agents.*` / `server.common.*`

# `voice` doit toujours résoudre vers le vrai code de ce module.
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

# `agents.builtin.base_agent` et `server.common.*` ne font pas partie de cette
# archive : on ne les stub qu'en repli, s'ils ne sont pas déjà importables
# (par exemple si ces tests tournent depuis le vrai dépôt neronOS complet).
# Le stub est ajouté en fin de sys.path pour ne jamais prendre le pas sur une
# implémentation réelle déjà présente.
try:
    importlib.import_module("agents.builtin.base_agent")
except ImportError:
    sys.path.append(str(STUBS_DIR))

try:
    importlib.import_module("server.common.service")
except ImportError:
    if str(STUBS_DIR) not in sys.path:
        sys.path.append(str(STUBS_DIR))


@pytest.fixture(autouse=True)
def _reset_voice_module_state():
    """
    stt/service.py et tts/service.py gardent un provider global (`_provider`).
    Sans reset, un test qui charge un fake provider peut en polluer un autre
    exécuté après lui. On réinitialise avant ET après chaque test.
    """
    import voice.stt.service as stt_service
    import voice.tts.service as tts_service

    stt_service._provider = None
    tts_service._provider = None
    yield
    stt_service._provider = None
    tts_service._provider = None


@pytest.fixture
def voice_yaml_factory(tmp_path):
    """Écrit un config/voice.yaml minimal dans tmp_path et retourne son chemin."""

    def _write(content: str) -> Path:
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        yaml_path = config_dir / "voice.yaml"
        yaml_path.write_text(content, encoding="utf-8")
        return yaml_path

    return _write


@pytest.fixture
def clean_env(monkeypatch):
    """Retire toutes les variables d'env VOICE_*/WHISPER_*/TTS_*/AUDIO_* connues.

    Nécessaire car `load_voice_config` lit l'environnement en priorité — sans
    ce nettoyage, l'environnement réel du poste d'exécution des tests pourrait
    fausser les assertions sur les valeurs par défaut / le YAML.
    """
    keys = [
        "VOICE_PROJECT_ROOT",
        "VOICE_STT_PROVIDER",
        "VOICE_TTS_PROVIDER",
        "VOICE_LANGUAGE",
        "WHISPER_MODEL",
        "WHISPER_LANGUAGE",
        "WHISPER_DOWNLOAD_ROOT",
        "STT_TIMEOUT",
        "AUDIO_MAX_SIZE_MB",
        "TTS_VOICE",
        "TTS_FORMAT",
        "TTS_MAX_CHARS",
    ]
    for key in keys:
        monkeypatch.delenv(key, raising=False)
    return monkeypatch
