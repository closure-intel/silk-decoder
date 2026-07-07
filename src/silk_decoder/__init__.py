"""In-house WeChat/Skype SILK (``.silk``) voice-note decoder.

Pure Python, standard-library only — deliberately no third-party codec packages
(no ``pilk`` / ``pysilk`` / unmaintained wrappers). See ``README.md`` for the trust and
provenance rationale, and ``ROADMAP.md`` for the status of the DSP core.

Public API::

    from silk_decoder import decode_to_wav, decode_to_pcm, parse_silk_container

Container parsing and WAV output are complete and tested; the SILK signal-decode core is
being implemented and validated bit-exact against reference vectors (until then, decode
calls raise :class:`SilkDecodeNotImplemented`).
"""

from silk_decoder.container import SilkContainer, parse_silk_container, read_silk_file
from silk_decoder.decoder import DEFAULT_SAMPLE_RATE, SilkFrameDecoder, decode_to_pcm, decode_to_wav
from silk_decoder.errors import (
    InvalidSilkFile,
    SilkDecodeNotImplemented,
    SilkError,
    TruncatedSilkFile,
)
from silk_decoder.wav import pcm_s16le_to_wav

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_SAMPLE_RATE",
    "InvalidSilkFile",
    "SilkContainer",
    "SilkDecodeNotImplemented",
    "SilkError",
    "SilkFrameDecoder",
    "TruncatedSilkFile",
    "decode_to_pcm",
    "decode_to_wav",
    "parse_silk_container",
    "pcm_s16le_to_wav",
    "read_silk_file",
]
