"""Parse the WeChat/Skype SILK v3 container framing (no signal decoding here).

A standalone SILK v3 file — what WeChat writes for voice notes (``*.aud`` / ``*.silk`` /
``*.slk``) — is laid out as::

    [0x02]            optional 1-byte Tencent prefix (WeChat only)
    "#!SILK_V3"       9-byte magic
    (int16_le nBytes, payload[nBytes]) *   one record per 20 ms audio frame
    ...
    int16_le 0xFFFF   optional explicit end-of-stream sentinel (nBytes < 0)

This matches the frame loop in the reference SILK SDK's ``test/Decoder.c``. Parsing the
container is completely separate from decoding the SILK bitstream inside each frame, so it
is implemented and tested on its own here; the DSP core consumes the ``frames`` this yields.

Nothing in this module is codec DSP — it is plain byte framing we author and own outright.
"""

import struct
from dataclasses import dataclass

from silk_decoder.errors import InvalidSilkFile, TruncatedSilkFile

#: WeChat prepends this single byte before the standard SILK magic. Raw (non-WeChat)
#: SILK v3 files omit it and begin directly with the magic.
TENCENT_PREFIX = b"\x02"

#: Standard SILK v3 stream marker.
SILK_V3_MAGIC = b"#!SILK_V3"

#: Each frame is length-prefixed by a little-endian *signed* 16-bit count. A negative
#: value (0xFFFF) is the reference SDK's explicit end-of-stream marker.
_FRAME_LENGTH_STRUCT = struct.Struct("<h")


@dataclass(frozen=True)
class SilkContainer:
    """The framed contents of a SILK v3 file, prior to signal decoding.

    :param frames: Each element is one frame's raw SILK payload (20 ms of audio),
        in stream order, ready to hand to the bitstream decoder.
    :param had_tencent_prefix: True if the file carried WeChat's leading ``0x02`` byte.
    :param trailing_bytes: Bytes left over after the last complete frame / EOF sentinel
        (normally 0; non-zero hints at a truncated or padded export).
    """

    frames: list[bytes]
    had_tencent_prefix: bool
    trailing_bytes: int


def parse_silk_container(*, data: bytes) -> SilkContainer:
    """Split a SILK v3 byte string into its per-frame payloads.

    :param data: Raw file bytes (with or without WeChat's ``0x02`` prefix).
    :returns: A :class:`SilkContainer` with the frames and provenance flags.
    :raises InvalidSilkFile: If the ``#!SILK_V3`` magic is absent.
    :raises TruncatedSilkFile: If a frame length points past the end of ``data``.
    """
    had_prefix = data[:1] == TENCENT_PREFIX and data[1 : 1 + len(SILK_V3_MAGIC)] == SILK_V3_MAGIC
    offset = len(TENCENT_PREFIX) if had_prefix else 0

    if data[offset : offset + len(SILK_V3_MAGIC)] != SILK_V3_MAGIC:
        raise InvalidSilkFile(
            f"missing '{SILK_V3_MAGIC.decode()}' magic (first bytes: {data[:12]!r}); not a SILK v3 stream"
        )
    offset += len(SILK_V3_MAGIC)

    frames: list[bytes] = []
    while offset + _FRAME_LENGTH_STRUCT.size <= len(data):
        (n_bytes,) = _FRAME_LENGTH_STRUCT.unpack_from(data, offset)
        offset += _FRAME_LENGTH_STRUCT.size
        if n_bytes < 0:  # explicit end-of-stream sentinel
            break
        frame_end = offset + n_bytes
        if frame_end > len(data):
            raise TruncatedSilkFile(
                f"frame at byte {offset} declares {n_bytes} bytes but only "
                f"{len(data) - offset} remain — file is truncated"
            )
        frames.append(data[offset:frame_end])
        offset = frame_end

    return SilkContainer(frames=frames, had_tencent_prefix=had_prefix, trailing_bytes=max(len(data) - offset, 0))


def read_silk_file(*, path: str) -> SilkContainer:
    """Read and parse a SILK v3 file from disk. Convenience wrapper over :func:`parse_silk_container`."""
    with open(path, "rb") as fh:
        return parse_silk_container(data=fh.read())
