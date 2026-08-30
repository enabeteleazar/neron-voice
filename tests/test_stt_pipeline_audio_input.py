import pytest

from voice.stt.pipeline.audio_input import validate_audio_input


def test_valid_extension_returns_lowercase_ext():
    assert validate_audio_input(b"data", "clip.WAV", max_size_mb=10) == ".wav"


@pytest.mark.parametrize("ext", [".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm"])
def test_all_documented_extensions_are_accepted(ext):
    assert validate_audio_input(b"x", f"clip{ext}", max_size_mb=10) == ext


def test_unsupported_extension_raises_value_error():
    with pytest.raises(ValueError, match="non supporté"):
        validate_audio_input(b"data", "clip.aiff", max_size_mb=10)


def test_missing_extension_raises_value_error():
    with pytest.raises(ValueError):
        validate_audio_input(b"data", "clip", max_size_mb=10)


def test_oversized_file_raises_value_error():
    payload = b"x" * (2 * 1024 * 1024)  # 2MB
    with pytest.raises(ValueError, match="trop volumineux"):
        validate_audio_input(payload, "clip.wav", max_size_mb=1)


def test_file_exactly_at_limit_is_accepted():
    max_size_mb = 1
    payload = b"x" * (max_size_mb * 1024 * 1024)
    assert validate_audio_input(payload, "clip.wav", max_size_mb=max_size_mb) == ".wav"


def test_file_one_byte_over_limit_is_rejected():
    max_size_mb = 1
    payload = b"x" * (max_size_mb * 1024 * 1024 + 1)
    with pytest.raises(ValueError):
        validate_audio_input(payload, "clip.wav", max_size_mb=max_size_mb)


def test_extension_check_happens_before_size_check():
    # Un fichier énorme mais avec une mauvaise extension doit lever une
    # erreur de format, pas une erreur de taille (ordre de validation).
    payload = b"x" * (5 * 1024 * 1024)
    with pytest.raises(ValueError, match="non supporté"):
        validate_audio_input(payload, "clip.aiff", max_size_mb=1)
