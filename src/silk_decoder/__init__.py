"""In-house WeChat/Skype SILK (``.silk``) voice-note decoder.

Decoding is done by a small native extension around the **vendored Skype SILK SDK
reference decoder** (``vendor/silk/``, BSD-3-Clause) — deliberately not the unmaintained
``pilk`` / ``pysilk`` PyPI wrappers. See ``README.md`` for the trust/provenance rationale
and ``PROVENANCE.md`` for the exact source + verification.

Public API::

    from silk_decoder import decode_to_wav, decode_to_pcm, parse_silk_container
"""

from silk_decoder.container import SilkContainer, parse_silk_container, read_silk_file
from silk_decoder.decoder import DEFAULT_SAMPLE_RATE, decode_to_pcm, decode_to_wav
from silk_decoder.errors import (
    InvalidSilkFile,
    SilkDecodeError,
    SilkError,
    TruncatedSilkFile,
)
from silk_decoder.wav import pcm_s16le_to_wav

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_SAMPLE_RATE",
    "InvalidSilkFile",
    "SilkContainer",
    "SilkDecodeError",
    "SilkError",
    "TruncatedSilkFile",
    "decode_to_pcm",
    "decode_to_wav",
    "parse_silk_container",
    "pcm_s16le_to_wav",
    "read_silk_file",
]
