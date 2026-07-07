# silk-decoder

An in-house decoder for **WeChat / Skype SILK (`.silk`) voice notes** — pure Python,
standard-library only, targeting Python 3.14. It exists so Closure never has to depend on an
unmaintained third-party SILK package (`pilk`, `pysilk`, and the various `silk-v3-decoder`
mirrors) to turn a WeChat voice message into playable/transcribable audio.

## Why this exists

WeChat voice notes are SILK v3 (the speech codec that later became the core of Opus). ffmpeg
cannot decode a standalone SILK stream — only SILK carried inside an Opus container — so some
decoder is required. The available Python packages are thin wrappers around a mirrored copy of
the old Skype SILK SDK C code: unmaintained, unclear provenance, not tested on current Python,
and they run C on untrusted forensic input. Rather than trust one of those, we build and own
the decoder ourselves.

**The SILK format is public and standardized** — Skype open-sourced it (BSD) in 2010 and it is
the normative basis of Opus (IETF RFC 6716). So decoding it ourselves is a matter of
implementing a published spec, not reverse-engineering anything.

## Design

- **Pure Python, zero runtime dependencies** — trivially runs on 3.14 (no C-extension ABI to
  chase, which was the concrete problem with the existing packages) and is fully auditable.
- **Consumed as a plain import** — `backend-service` (already Python 3.14) calls
  `decode_to_wav(...)` directly in its audio pipeline. Pure Python means no C-extension ABI to
  match a Python version — the exact problem the existing packages had.
- **Correctness is gated on reference test vectors** (see below). For forensic evidence a
  plausible-but-wrong decode is worse than none, so the DSP is validated bit-exact, not trusted
  because "it runs."

## Status

| Component | Status |
|---|---|
| SILK v3 container framing (Tencent `0x02` prefix, `#!SILK_V3`, length-prefixed frames, EOF) | ✅ done + tested |
| PCM → WAV output | ✅ done + tested |
| Public API (`decode_to_pcm` / `decode_to_wav` / `parse_silk_container`) | ✅ done + tested |
| Conformance harness (bit-exact vs reference vectors) | ✅ scaffolded (skips until vectors present) |
| **SILK signal-decode DSP** (range coder → NLSF/LPC → LTP → excitation → synthesis → resample) | ⏳ staged — see `ROADMAP.md` |

Until the DSP core lands, `decode_to_*` raises `SilkDecodeNotImplemented` rather than emitting
anything that could be mistaken for a real decode.

## Usage

```python
from silk_decoder import decode_to_wav, parse_silk_container

info = parse_silk_container(data=open("voice.silk", "rb").read())   # framing/inspection, works today
wav = decode_to_wav(data=open("voice.silk", "rb").read())            # full decode, once the DSP core lands
```

Consumed as a library from `backend-service` — no CLI/subprocess.

## Layout

```
src/silk_decoder/
  container.py   SILK v3 framing (ours)
  wav.py         PCM -> WAV (ours)
  decoder.py     decode pipeline + DSP stage plan
  errors.py      typed exceptions
tests/           unit tests + tests/conformance/ (vector oracle)
vectors/         reference <name>.silk + <name>.pcm pairs (dev-only oracle, not shipped)
```

## Development

```
pip install -e ".[dev]"
pytest
```

## CI

- **`ci.yml`** (push / PR): `ruff` lint + format check and `pytest` on Python 3.14, plus a build
  job that builds the wheel, installs it in a clean env, and imports it — so a release can never
  ship something that won't install.
- **`release.yml`** (on a `MAJOR.MINOR.PATCH` tag): checks the tag matches the `pyproject.toml`
  version, re-runs tests, builds, and publishes a GitHub Release with the sdist + wheel attached.

## Consuming it (backend-service)

First-party, **git-installed** — the same pattern `backend-service` already uses for
`msg-parser`. No PyPI. Add to `requirements/base.requirements.txt`:

```
silk-decoder @ git+https://github.com/closure-intel/silk-decoder.git@0.1.0  # WeChat SILK voice-note decoder
```

`uv pip install` builds it from the pinned tag at image-build time. Pure Python means no
wheel/ABI to match a Python version, and the repo access/auth already set up for `msg-parser`
covers this too.

## Releasing

1. Bump `version` in `pyproject.toml`.
2. Tag and push: `git tag 0.2.0 && git push origin 0.2.0` (no `v` prefix, to match msg-parser).
3. `release.yml` verifies + tests + builds + publishes the GitHub Release.
4. Bump the pinned `@<version>` in backend-service's requirements to pick it up.

## License

BSD-3-Clause. The SILK algorithm itself was released by Skype under a BSD-style license and is
specified in IETF RFC 6716 (Opus).
