"""Tests for the PCM->WAV wrapper.

Regression class guarded: the RIFF/WAV header we emit is well-formed and round-trips
through a standard WAV reader with the right rate/channels/width and byte-identical samples.
"""

import io
import wave

import pytest

from silk_decoder.wav import pcm_s16le_to_wav


def test_wav_header_is_wellformed_and_roundtrips() -> None:
    pcm = bytes(range(0, 256)) * 4  # 1024 bytes = 512 s16 samples
    wav = pcm_s16le_to_wav(pcm=pcm, sample_rate=24000)

    assert wav[:4] == b"RIFF"
    assert wav[8:12] == b"WAVE"
    assert len(wav) == 44 + len(pcm)

    with wave.open(io.BytesIO(wav), "rb") as reader:
        assert reader.getframerate() == 24000
        assert reader.getnchannels() == 1
        assert reader.getsampwidth() == 2
        assert reader.readframes(reader.getnframes()) == pcm


def test_empty_pcm_produces_valid_empty_wav() -> None:
    wav = pcm_s16le_to_wav(pcm=b"", sample_rate=24000)
    assert len(wav) == 44
    with wave.open(io.BytesIO(wav), "rb") as reader:
        assert reader.getnframes() == 0


def test_invalid_sample_rate_rejected() -> None:
    with pytest.raises(ValueError):
        pcm_s16le_to_wav(pcm=b"\x00\x00", sample_rate=0)
