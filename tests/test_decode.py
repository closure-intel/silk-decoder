"""End-to-end decode through the public API, using the committed vector.

Regression class guarded: container -> native decode -> WAV produces valid, correctly-shaped
audio, and non-SILK input is rejected cleanly rather than fed to the decoder.
"""

import io
import pathlib
import wave

import pytest

from silk_decoder import InvalidSilkFile, decode_to_pcm, decode_to_wav

_VECTOR = pathlib.Path(__file__).resolve().parent.parent / "vectors" / "wechat_tone_2s_24k.silk"


def test_decode_to_wav_is_valid_2s_audio() -> None:
    wav = decode_to_wav(data=_VECTOR.read_bytes())
    with wave.open(io.BytesIO(wav), "rb") as reader:
        assert reader.getframerate() == 24000
        assert reader.getnchannels() == 1
        assert reader.getsampwidth() == 2
        assert reader.getnframes() == 48000  # exactly 2.00 s @ 24 kHz


def test_decode_rejects_non_silk_input() -> None:
    with pytest.raises(InvalidSilkFile):
        decode_to_pcm(data=b"this is not a silk stream")
