from __future__ import annotations

import io
import shutil
import tempfile
import wave
from pathlib import Path

from piper import PiperVoice

from voice.audio.codecs import MIMETYPE_BY_FORMAT
from voice.audio.converters import convert_wav_to_mp3
from voice.config import TtsConfig
from voice.models import SpeechResult
from voice.tts.providers.base import TtsProvider

def _voices_dir() -> Path:
    directory = Path.home() / ".local" / "share" / "piper-voices"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


class PiperFfmpegProvider(TtsProvider):
    def __init__(self, config: TtsConfig) -> None:
        self.config = config
        self._voices_dir = _voices_dir()
        # Voix chargee UNE SEULE FOIS a l'instanciation du provider, plutot
        # que relancee en sous-processus a chaque synthese (~7 s de recharge
        # du modele depuis le disque a chaque appel, mesure le 13/08).
        model_path = self._voices_dir / f"{self.config.voice}.onnx"
        config_path = self._voices_dir / f"{self.config.voice}.onnx.json"
        self._voice = PiperVoice.load(model_path, config_path=config_path)

    def name(self) -> str:
        return f"piper:{self.config.voice}"

    def synthesize(self, text: str, fmt: str = "mp3") -> SpeechResult:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav_file:
            self._voice.synthesize_wav(text, wav_file)
        wav_bytes = buf.getvalue()

        if fmt == "wav":
            return SpeechResult(
                audio=wav_bytes,
                format="wav",
                metadata={"mimetype": MIMETYPE_BY_FORMAT["wav"], "engine": self.name()},
            )

        # ffmpeg n'a besoin que d'un chemin en entree/sortie : on ecrit le
        # wav en memoire sur disque juste pour cette conversion.
        with tempfile.TemporaryDirectory(prefix="neron_tts_") as tmpdir:
            wav_path = Path(tmpdir) / "out.wav"
            wav_path.write_bytes(wav_bytes)
            mp3_path = Path(tmpdir) / "out.mp3"
            convert_wav_to_mp3(wav_path, mp3_path)
            return SpeechResult(
                audio=mp3_path.read_bytes(),
                format="mp3",
                metadata={"mimetype": MIMETYPE_BY_FORMAT["mp3"], "engine": self.name()},
            )
