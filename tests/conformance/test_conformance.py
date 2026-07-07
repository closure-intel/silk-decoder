"""Bit-exact conformance harness — the correctness gate for the DSP core.

This is how we make "we wrote the codec ourselves" trustworthy for evidence: for each
reference ``vectors/<name>.silk`` there is a known-good ``vectors/<name>.pcm`` (signed-16-bit
LE mono), produced by the reference decoder as a *development-time oracle only* — it is never
shipped or imported at runtime. Our pure-Python decoder must reproduce that PCM byte-for-byte.

Until reference vectors are dropped into ``vectors/`` (and the DSP stages land), every case
skips — so CI stays green while making the missing coverage explicit rather than silently
absent. See ROADMAP.md for how vectors are sourced.
"""

import pathlib

import pytest

from silk_decoder.decoder import decode_to_pcm
from silk_decoder.errors import SilkDecodeNotImplemented

_VECTORS_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "vectors"


def _vector_pairs() -> list[tuple[pathlib.Path, pathlib.Path]]:
    if not _VECTORS_DIR.is_dir():
        return []
    return [(silk, silk.with_suffix(".pcm")) for silk in sorted(_VECTORS_DIR.glob("*.silk"))]


_PAIRS = _vector_pairs()


@pytest.mark.skipif(not _PAIRS, reason="no reference vectors in vectors/ yet (see ROADMAP.md)")
@pytest.mark.parametrize("silk_path,pcm_path", _PAIRS, ids=lambda p: p.name)
def test_decode_matches_reference_pcm(silk_path: pathlib.Path, pcm_path: pathlib.Path) -> None:
    assert pcm_path.exists(), f"missing expected PCM oracle for {silk_path.name}"
    expected = pcm_path.read_bytes()
    try:
        actual = decode_to_pcm(data=silk_path.read_bytes())
    except SilkDecodeNotImplemented:
        pytest.skip("DSP core not implemented yet — see ROADMAP.md")
    assert actual == expected, f"decoded PCM for {silk_path.name} does not match the reference bit-for-bit"
