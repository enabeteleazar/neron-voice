import struct
import wave

import pytest

from voice.audio.converters.ffmpeg import convert_wav_to_mp3, find_ffmpeg


def _write_silent_wav(path, seconds: float = 0.1, framerate: int = 16000) -> None:
    n_frames = int(seconds * framerate)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(framerate)
        wf.writeframes(struct.pack("<" + "h" * n_frames, *([0] * n_frames)))


def test_find_ffmpeg_returns_a_path_when_installed():
    # Suppose ffmpeg installé sur la machine qui exécute la suite (c'est le
    # cas sur homebox). Si ce test échoue en CI, c'est un problème
    # d'environnement à documenter, pas une régression du code.
    path = find_ffmpeg()
    assert path


def test_find_ffmpeg_raises_when_not_on_path(monkeypatch):
    import shutil

    monkeypatch.setattr(shutil, "which", lambda _: None)
    with pytest.raises(RuntimeError, match="ffmpeg introuvable"):
        find_ffmpeg()


def test_convert_wav_to_mp3_produces_valid_mp3(tmp_path):
    wav_path = tmp_path / "in.wav"
    mp3_path = tmp_path / "out.mp3"
    _write_silent_wav(wav_path)

    convert_wav_to_mp3(wav_path, mp3_path)

    assert mp3_path.exists()
    assert mp3_path.stat().st_size > 0
    # ID3 ou frame-sync MPEG : les deux en-têtes possibles pour un mp3 valide.
    header = mp3_path.read_bytes()[:3]
    assert header == b"ID3" or header[:2] == b"\xff\xfb" or header[:1] == b"\xff"


def test_convert_wav_to_mp3_raises_on_missing_input(tmp_path):
    wav_path = tmp_path / "does-not-exist.wav"
    mp3_path = tmp_path / "out.mp3"
    with pytest.raises(RuntimeError, match="ffmpeg a échoué"):
        convert_wav_to_mp3(wav_path, mp3_path)
