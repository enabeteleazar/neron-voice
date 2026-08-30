from voice.normalization.french import normalize_french_text


def test_collapses_multiple_spaces():
    assert normalize_french_text("Bonjour   le    monde") == "Bonjour le monde"


def test_strips_leading_trailing_whitespace():
    assert normalize_french_text("   Bonjour   ") == "Bonjour"


def test_removes_space_before_punctuation():
    assert normalize_french_text("Salut , ça va ?") == "Salut, ça va?"


def test_neron_gets_proper_accent_and_capital():
    assert normalize_french_text("demande à neron de répondre") == "Demande à Néron de répondre"


def test_neron_with_accent_already_present_is_normalized_too():
    assert "Néron" in normalize_french_text("bonjour NÉRON")


def test_ok_is_uppercased():
    assert normalize_french_text("ok, ça marche") == "OK, ça marche"


def test_ok_as_substring_is_not_touched():
    # "loki" ne doit pas devenir "loKI" : \b(?:ok)\b est bien un mot entier.
    assert normalize_french_text("loki") == "Loki"


def test_first_letter_capitalized():
    assert normalize_french_text("bonjour") == "Bonjour"


def test_first_letter_untouched_if_not_alpha():
    assert normalize_french_text("42 est la réponse") == "42 est la réponse"


def test_empty_string_returns_empty():
    assert normalize_french_text("") == ""


def test_none_like_falsy_input_does_not_crash():
    # La fonction fait `text or ""` en interne : elle doit survivre à un None.
    assert normalize_french_text(None) == ""  # type: ignore[arg-type]
