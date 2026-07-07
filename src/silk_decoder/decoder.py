"""Top-level SILK decode pipeline: container -> native decode -> PCM -> WAV.

Container framing (:mod:`silk_decoder.container`) is parsed in Python; the per-frame signal
decode is performed by the native :mod:`silk_decoder._silk` extension, which drives the
vendored Skype SILK SDK reference decoder (see ``vendor/silk/`` and ``PROVENANCE.md``). WAV
output is :mod:`silk_decoder.wav`.
"""

from silk_decoder.container import parse_silk_container
from silk_decoder.errors import SilkDecodeError
from silk_decoder.wav import pcm_s16le_to_wav

#: WeChat voice notes are mono and the SILK bitstream carries no playback rate, so we decode
#: at WeChat's canonical rate unless the caller overrides it.
DEFAULT_SAMPLE_RATE = 24000


def _native():
    """Import the compiled extension, with a clear error if it hasn't been built."""
    try:
        from silk_decoder import _silk
    except ImportError as exc:
        raise SilkDecodeError(
            "the native SILK extension (silk_decoder._silk) is not built — "
            "install the package ('pip install .') or build in place "
            "('python setup.py build_ext --inplace')"
        ) from exc
    return _silk


def decode_to_pcm(*, data: bytes, sample_rate: int = DEFAULT_SAMPLE_RATE) -> bytes:
    """Decode a full SILK v3 file to raw signed-16-bit LE mono PCM.

    :param data: Raw ``.silk`` file bytes (with or without WeChat's ``0x02`` prefix).
    :param sample_rate: Target output rate in Hz.
    :returns: Concatenated PCM for every frame.
    :raises InvalidSilkFile: If the input is not a SILK v3 stream.
    :raises TruncatedSilkFile: If a frame runs past the end of the data.
    :raises SilkDecodeError: If the native decoder fails or is not built.
    """
    container = parse_silk_container(data=data)
    silk = _native()
    try:
        return silk.decode_frames(container.frames, sample_rate)
    except silk.SilkNativeError as exc:
        raise SilkDecodeError(str(exc)) from exc


def decode_to_wav(*, data: bytes, sample_rate: int = DEFAULT_SAMPLE_RATE) -> bytes:
    """Decode a full SILK v3 file straight to an in-memory WAV.

    :param data: Raw ``.silk`` file bytes.
    :param sample_rate: Target output rate in Hz.
    :returns: A complete WAV file (RIFF header + PCM).
    """
    return pcm_s16le_to_wav(pcm=decode_to_pcm(data=data, sample_rate=sample_rate), sample_rate=sample_rate)
