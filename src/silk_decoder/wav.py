"""Wrap raw PCM samples in a canonical RIFF/WAV container.

The SILK decoder emits headerless signed-16-bit little-endian PCM; downstream tooling
(ffmpeg, transcription, playback) wants a real WAV. This is the same 44-byte header the
Closure worker already writes for its other in-house-decoded codecs (e.g. GTL V26), kept
here so this package is self-contained and has no dependency on the worker.
"""

import struct

# RIFF / WAVE PCM header: little-endian, 16-bit PCM, fixed 44-byte layout.
_WAV_HEADER_STRUCT = struct.Struct("<4sI4s4sIHHIIHH4sI")
_PCM_FORMAT_TAG = 1
_BITS_PER_SAMPLE = 16


def pcm_s16le_to_wav(*, pcm: bytes, sample_rate: int, channels: int = 1) -> bytes:
    """Prepend a canonical 44-byte RIFF/WAV header to signed-16-bit LE PCM.

    :param pcm: Raw signed-16-bit little-endian interleaved PCM samples.
    :param sample_rate: Sample rate in Hz the PCM was decoded at (24000 for WeChat).
    :param channels: Channel count (WeChat voice notes are mono).
    :returns: A complete in-memory WAV file.
    """
    if sample_rate <= 0:
        raise ValueError(f"sample_rate must be positive, got {sample_rate}")
    if channels <= 0:
        raise ValueError(f"channels must be positive, got {channels}")

    data_len = len(pcm)
    block_align = channels * (_BITS_PER_SAMPLE // 8)
    byte_rate = sample_rate * block_align
    header = _WAV_HEADER_STRUCT.pack(
        b"RIFF",
        36 + data_len,  # RIFF chunk size = 4 ("WAVE") + (8 + 16 fmt) + (8 + data)
        b"WAVE",
        b"fmt ",
        16,  # PCM fmt chunk size
        _PCM_FORMAT_TAG,
        channels,
        sample_rate,
        byte_rate,
        block_align,
        _BITS_PER_SAMPLE,
        b"data",
        data_len,
    )
    return header + pcm
