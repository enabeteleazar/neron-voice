import pytest

from voice.tts.pipeline.text import validate_tts_text


def test_strips_surrounding_whitespace():
    assert validate_tts_text("  Bonjour  ", max_chars=100) == "Bonjour"


def test_empty_string_raises_value_error():
    with pytest.raises(ValueError, match="vide"):
        validate_tts_text("", max_chars=100)


def test_whitespace_only_string_raises_value_error():
    with pytest.raises(ValueError, match="vide"):
        validate_tts_text("   \n\t  ", max_chars=100)


def test_none_like_input_raises_value_error():
    with pytest.raises(ValueError):
        validate_tts_text(None, max_chars=100)  # type: ignore[arg-type]


def test_text_over_limit_raises_value_error():
    with pytest.raises(ValueError, match="trop long"):
        validate_tts_text("a" * 101, max_chars=100)


def test_text_exactly_at_limit_is_accepted():
    text = "a" * 100
    # Le texte est normalisé (majuscule initiale), on vérifie que la longueur est préservée
    assert validate_tts_text(text, max_chars=100) == "A" + "a" * 99


def test_text_under_limit_is_returned_unchanged_besides_strip():
    assert validate_tts_text("Bonjour Néron", max_chars=100) == "Bonjour Néron"
