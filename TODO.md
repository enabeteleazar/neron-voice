# TODO — server/voice

## Fait (P0, 26/08)
- [x] `_project_root()` corrigé (`parents[4]` → `parents[3]`), avec log au chargement si le YAML est introuvable/invalide, et override `VOICE_PROJECT_ROOT` pour les tests/déploiements atypiques.
- [x] Timeout réel sur `stt.transcribe()` via `asyncio.wait_for(config.timeout)`.
- [x] `/transcribe` renvoie un vrai code HTTP d'erreur (`400`/`504`/`422`) au lieu de `200` + `success: false`, aligné sur `/synthesize`.
- [x] Suite de tests pytest (89 tests, ~87% de couverture sur `voice/`).

## P1 — avant un tag `v0.1.0`
- [ ] Brancher `normalize_french_text` dans `tts/pipeline/text.py::validate_tts_text` (ou documenter clairement pourquoi ce n'est pas encore fait — actuellement le README promet un comportement que le code ne fait pas).
- [ ] `TTSAgent` ne distingue pas `error_type` (validation vs interne) comme `STTAgent` le fait maintenant. Pas bloquant tant que `/synthesize` reste toujours en 422 sur échec, mais si un jour on veut différencier (ex. texte vide → 400), reprendre le même pattern que `STTAgent.transcribe`.
- [ ] Découpler les imports eager de `voice/__init__.py` (`from voice import stt, tts`) qui forcent `piper` et `faster-whisper` comme dépendances dures de test même pour tester une fonction pure comme `normalize_french_text`. Piste : imports paresseux dans `stt/providers/__init__.py` et `tts/providers/__init__.py` (import du provider concret seulement à l'instanciation, pas au chargement du package).

## P2 — plus tard
- [ ] Lock/versioning autour de `_provider` (stt et tts) pour éviter une race si `/reload` est appelé pendant une requête en cours.
- [ ] Le timeout ajouté protège la requête HTTP mais pas le pool de threads : un appel `faster-whisper` réellement bloqué occupe son worker jusqu'à ce qu'il rende la main tout seul (pas d'annulation dure possible sur un thread natif). Si ça se manifeste en usage réel, envisager une isolation par process pour permettre un vrai `kill`.
- [ ] Vérifier si `create_service_app` (server.common.service, hors périmètre de ce zip) protège déjà `/reload` par une forme d'auth réseau (Tailscale) — sinon, l'endpoint est appelable par quiconque a accès au service.
- [ ] `SttConfig.timeout` par défaut à 60s : valider que c'est le bon ordre de grandeur pour les clips vocaux réels une fois en usage.

## Limites connues de la suite de tests
- `stt/providers/whisper.py` et `tts/providers/piper.py` sont couverts à 33%/45% seulement : le reste, c'est le vrai chargement de modèle et l'inférence, qui nécessiteraient des fichiers de modèle réels sur disque pour être testés sans mock — hors périmètre d'une suite unitaire rapide. Les deux fichiers restent testés côté contrat (via `SttProvider`/`TtsProvider`) grâce aux fakes dans `test_stt_service.py`/`test_tts_service.py`.
- `agents.builtin.base_agent` et `server.common.*` ne font pas partie de `voice.zip` : `tests/stubs/` fournit des doublons minimaux pour permettre l'exécution isolée. Si le vrai code de ces modules diverge du contrat reproduit ici (champs d'`AgentResult`, signature de `create_service_app`), ces tests ne le détecteront pas — à relancer aussi depuis le monorepo complet de temps en temps pour vérifier que les stubs collent toujours.
