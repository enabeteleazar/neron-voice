from __future__ import annotations


def validate_tts_text(text: str, max_chars: int) -> str:
    from voice.normalization.french import normalize_french_text
    normalized = normalize_french_text((text or "").strip())
    if not normalized:
        raise ValueError("Texte vide")
    if len(normalized) > max_chars:
        raise ValueError(f"Texte trop long : {len(normalized)} > {max_chars}")
    return normalized
