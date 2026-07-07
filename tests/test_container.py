"""Tests for the SILK v3 container framing parser.

Regression class guarded: the byte-level framing (Tencent prefix detection, magic
validation, length-prefixed frame splitting, EOF sentinel, truncation) — the part we
author ourselves, independent of the codec DSP.
"""

import struct

import pytest

from silk_decoder.container import SILK_V3_MAGIC, TENCENT_PREFIX, parse_silk_container
from silk_decoder.errors import InvalidSilkFile, TruncatedSilkFile

_EOF_SENTINEL = struct.pack("<h", -1)


def _frame(payload: bytes) -> bytes:
    """Build one length-prefixed container record."""
    return struct.pack("<h", len(payload)) + payload


def test_parses_frames_with_tencent_prefix() -> None:
    data = TENCENT_PREFIX + SILK_V3_MAGIC + _frame(b"abc") + _frame(b"de") + _EOF_SENTINEL
    container = parse_silk_container(data=data)
    assert container.frames == [b"abc", b"de"]
    assert container.had_tencent_prefix is True
    assert container.trailing_bytes == 0


def test_parses_frames_without_prefix() -> None:
    data = SILK_V3_MAGIC + _frame(b"xy")
    container = parse_silk_container(data=data)
    assert container.frames == [b"xy"]
    assert container.had_tencent_prefix is False
    assert container.trailing_bytes == 0


def test_empty_stream_has_no_frames() -> None:
    container = parse_silk_container(data=SILK_V3_MAGIC)
    assert container.frames == []


def test_missing_magic_raises() -> None:
    with pytest.raises(InvalidSilkFile):
        parse_silk_container(data=b"NOT A SILK FILE AT ALL")


def test_lone_prefix_byte_is_not_mistaken_for_silk() -> None:
    # 0x02 followed by non-magic must NOT be treated as a prefixed SILK file.
    with pytest.raises(InvalidSilkFile):
        parse_silk_container(data=TENCENT_PREFIX + b"NOPE not magic")


def test_truncated_frame_raises() -> None:
    data = SILK_V3_MAGIC + struct.pack("<h", 10) + b"short"  # declares 10 bytes, supplies 5
    with pytest.raises(TruncatedSilkFile):
        parse_silk_container(data=data)


def test_frames_preserve_binary_payload() -> None:
    payload = bytes(range(256))  # all byte values, incl. would-be length/sentinel bytes
    container = parse_silk_container(data=SILK_V3_MAGIC + _frame(payload))
    assert container.frames == [payload]
