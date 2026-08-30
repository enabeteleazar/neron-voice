"""
Stub de test pour `server.common.paths`.

Ce module réel n'est pas fourni dans l'archive `voice.zip` (il vit ailleurs
dans le monorepo neronOS). Cette version minimale reproduit uniquement le
contrat utilisé par `voice/app.py` (lire un fichier VERSION à côté du module
appelant) afin que la suite de tests puisse importer `app.py` en isolation.

À NE PAS UTILISER EN PRODUCTION — si `server.common` est déjà importable
(dans le vrai dépôt), il prend le pas sur ce stub car son répertoire est
ajouté après le vrai chemin dans `sys.path` (voir tests/conftest.py).
"""
from __future__ import annotations

from pathlib import Path


def service_version(file: str) -> str:
    version_file = Path(file).resolve().parent / "VERSION"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return "0.0.0-test"
