from pathlib import Path

from voice.config.loader import (
    SttConfig,
    TtsConfig,
    _project_root,
    load_voice_config,
)


def test_project_root_points_to_repo_root_not_one_level_above():
    """
    Régression P0 : `_project_root()` pointait un niveau trop haut
    (`parents[4]`), ce qui faisait échouer silencieusement la résolution de
    `config/voice.yaml`. La racine attendue est celle qui contient à la fois
    `server/` (où vit ce module) et `config/` (où vit le yaml) — cohérent
    avec le default `download_root = "/etc/neronOS/data/models"`.
    """
    root = _project_root()
    module_file = Path(__file__).resolve().parents[1] / "config" / "loader.py"
    # loader.py est à repo_root/server/voice/config/loader.py -> repo_root
    # doit être son 3e parent.
    assert root == module_file.resolve().parents[3]


def test_project_root_override_via_env(clean_env, tmp_path):
    clean_env.setenv("VOICE_PROJECT_ROOT", str(tmp_path))
    assert _project_root() == tmp_path


def test_defaults_when_no_yaml_and_no_env(clean_env, tmp_path):
    config = load_voice_config(tmp_path / "does-not-exist.yaml")
    assert config.stt == SttConfig()
    assert config.tts == TtsConfig()
    assert config.language.default == "fr-FR"


def test_yaml_values_are_applied(clean_env, voice_yaml_factory):
    yaml_path = voice_yaml_factory(
        """
stt:
  provider: whisper
  model: small
  language: en
  timeout: 30
  max_size_mb: 20
tts:
  provider: piper
  voice: fr_FR-upmc-medium
  format: wav
  max_chars: 500
language:
  default: en-US
"""
    )
    config = load_voice_config(yaml_path)
    assert config.stt.model == "small"
    assert config.stt.language == "en"
    assert config.stt.timeout == 30
    assert config.stt.max_size_mb == 20
    assert config.tts.voice == "fr_FR-upmc-medium"
    assert config.tts.format == "wav"
    assert config.tts.max_chars == 500
    assert config.language.default == "en-US"


def test_env_vars_take_precedence_over_yaml(clean_env, voice_yaml_factory):
    yaml_path = voice_yaml_factory(
        """
stt:
  model: small
tts:
  voice: fr_FR-upmc-medium
"""
    )
    clean_env.setenv("WHISPER_MODEL", "large-v3")
    clean_env.setenv("TTS_VOICE", "fr_FR-siwis-medium")

    config = load_voice_config(yaml_path)
    assert config.stt.model == "large-v3"
    assert config.tts.voice == "fr_FR-siwis-medium"


def test_missing_yaml_falls_back_to_defaults_and_warns(clean_env, tmp_path, caplog):
    missing_path = tmp_path / "config" / "voice.yaml"
    with caplog.at_level("WARNING", logger="voice.config"):
        config = load_voice_config(missing_path)
    assert config.stt == SttConfig()
    assert any("introuvable" in record.message for record in caplog.records)


def test_invalid_yaml_shape_falls_back_to_defaults_and_warns(clean_env, tmp_path, caplog):
    yaml_path = tmp_path / "voice.yaml"
    yaml_path.write_text("- juste\n- une\n- liste\n", encoding="utf-8")
    with caplog.at_level("WARNING", logger="voice.config"):
        config = load_voice_config(yaml_path)
    assert config.stt == SttConfig()
    assert any("invalide" in record.message for record in caplog.records)


def test_unsupported_provider_in_yaml_is_not_validated_at_load_time(clean_env, voice_yaml_factory):
    # load_voice_config() ne valide pas le provider lui-même : c'est
    # stt/tts.service qui lève une RuntimeError plus tard. On verrouille ce
    # comportement ici pour que la surprise n'arrive pas ailleurs sans test.
    yaml_path = voice_yaml_factory("stt:\n  provider: vosk\n")
    config = load_voice_config(yaml_path)
    assert config.stt.provider == "vosk"
