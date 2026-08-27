# NeronOS Voice

`server/voice` regroupe la couche audio de NeronOS: transcription STT, synthese
TTS, providers vocaux, validation audio et normalisation de texte.

## Architecture

- `voice.stt`: API interne stable pour la transcription.
- `voice.tts`: API interne stable pour la synthese vocale.
- `voice.audio`: codecs, conversions et points d'extension de traitement audio.
- `voice.normalization`: normalisation linguistique, avec une premiere couche
  francaise.
- `voice.config`: chargement de `config/voice.yaml` et variables d'environnement.
- `voice.adapters`: adaptateurs pour les anciens agents Core/Gateway.
- `app.py`: daemon FastAPI conserve pour compatibilite HTTP.

## API Python

```python
from voice import stt, tts

await stt.transcribe(audio_bytes, "clip.webm")
# -> TranscriptionResult(text, language, confidence, metadata)

await tts.speak("Bonjour", {"format": "mp3"})
# -> SpeechResult(audio, format, duration, metadata)
```

Le reste de NeronOS ne doit pas connaitre le moteur concret. Les providers
actuels sont:

- STT: `whisper`, via `faster-whisper`.
- TTS: `piper`, avec conversion MP3 via `ffmpeg`.

## API HTTP conservee

Le daemon `server/voice/app.py` garde les endpoints utilises par les clients
existants:

- `GET /health`
- `POST /transcribe`
- `POST /synthesize`
- `POST /reload`

## Configuration

La configuration principale est `config/voice.yaml`.

```yaml
stt:
  provider: whisper
  model: base
  language: fr

tts:
  provider: piper
  voice: fr_FR-siwis-medium
  format: mp3

language:
  default: fr-FR
```

Les variables d'environnement historiques restent supportees:
`WHISPER_MODEL`, `WHISPER_LANGUAGE`, `WHISPER_DOWNLOAD_ROOT`,
`AUDIO_MAX_SIZE_MB`, `TTS_VOICE`, `TTS_FORMAT`, `TTS_MAX_CHARS`.

## Tests

```bash
pip install -r requirements-dev.txt --break-system-packages
pytest
```

89 tests, ~87% de couverture sur `voice/`. Les parties non couvertes sont le
chargement/inférence réels de `faster-whisper` et `piper` (nécessitent des
fichiers de modèle sur disque) — testées côté contrat via des fakes plutôt
qu'en conditions réelles. Voir `TODO.md` pour le détail des limites connues.

`agents.builtin.base_agent` et `server.common.*` ne font pas partie de ce
module : `tests/stubs/` fournit des doublons minimaux utilisés seulement en
repli si ces packages ne sont pas déjà sur le `PYTHONPATH` (ex. en lançant
les tests depuis le monorepo complet, les vraies implémentations prennent le
dessus).

## Ajouter un provider

1. Creer un provider dans `stt/providers` ou `tts/providers`.
2. Implementer l'interface `SttProvider` ou `TtsProvider`.
3. Ajouter la selection dans `stt/service.py` ou `tts/service.py`.
4. Documenter les options dans `config/voice.yaml`.
5. Ajouter des tests unitaires sans charger de modele lourd.
