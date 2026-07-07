"""Bit-exact conformance / regression gate for the decoder.

For each ``vectors/<name>.silk`` there is a known-good ``vectors/<name>.pcm`` (signed-16-bit
LE mono). Decoding must reproduce that PCM byte-for-byte. This guards the whole native path
(container parsing + the vendored SDK + our wrapper + the build) against any regression.

Add new vectors by dropping a ``.silk`` and its decoded ``.pcm`` into ``vectors/``.
"""

import pathlib

import pytest

from silk_decoder import decode_to_pcm

_VECTORS_DIR = pathlib.Path(__file__).resolve().parents[2] / "vectors"


def _vector_pairs() -> list[tuple[pathlib.Path, pathlib.Path]]:
    if not _VECTORS_DIR.is_dir():
        return []
    return [(silk, silk.with_suffix(".pcm")) for silk in sorted(_VECTORS_DIR.glob("*.silk"))]


_PAIRS = _vector_pairs()


@pytest.mark.skipif(not _PAIRS, reason="no reference vectors in vectors/")
@pytest.mark.parametrize("silk_path,pcm_path", _PAIRS, ids=lambda p: p.name)
def test_decode_matches_reference_pcm(silk_path: pathlib.Path, pcm_path: pathlib.Path) -> None:
    assert pcm_path.exists(), f"missing expected PCM for {silk_path.name}"
    expected = pcm_path.read_bytes()
    actual = decode_to_pcm(data=silk_path.read_bytes())
    assert actual == expected, f"decoded PCM for {silk_path.name} does not match the reference bit-for-bit"
