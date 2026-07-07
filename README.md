# silk-decoder

An in-house decoder for **WeChat / Skype SILK (`.silk`) voice notes** — decodes a SILK v3
stream to PCM/WAV so Closure can play and transcribe WeChat voice messages, without depending
on an unmaintained third-party SILK package (`pilk`, `pysilk`, the `silk-v3-decoder` mirrors).

## Why this exists

WeChat voice notes are **standalone SILK v3** (the speech codec that later became the core of
Opus). Two constraints force a dedicated decoder:

- **ffmpeg can't decode standalone SILK** — only SILK carried inside an Opus container.
- **Opus/xiph's SILK can't either** — when SILK was folded into Opus its entropy coder and
  framing were replaced, so the modern reference cannot read a v3 stream. Only the original
  Skype SILK SDK decodes SILK v3.

The available Python packages are thin, unmaintained wrappers around a mirrored copy of that
SDK — unclear provenance, not built for current Python, running C on untrusted forensic input.
So instead we **vendor the canonical Skype SILK SDK reference decoder (BSD-3-Clause) into this
repo, build it ourselves, and wrap it thinly.** We own and control the source and the build; we
don't trust a random package, and we don't re-implement a speech codec by hand (which would risk
subtly-wrong audio in evidence). See [`PROVENANCE.md`](PROVENANCE.md) for exactly what's vendored
and how it's verified.

## How it works

```
container.py   parse WeChat framing (0x02 prefix, #!SILK_V3, length-prefixed frames)   [pure Python]
   -> _silk    native wrapper drives the vendored Skype SILK SDK, frame -> PCM          [C, vendored SDK]
   -> wav.py   wrap signed-16-bit mono PCM in a RIFF/WAV header                          [pure Python]
```

The only hand-written C is the ~150-line wrapper (`_silkmodule.c`); it implements no codec DSP.
The extension builds from source at install time, so it targets whatever Python installs it
(3.14 in backend-service) — no prebuilt-wheel/ABI mismatch, which was the existing packages' flaw.

## Status

| Component | Status |
|---|---|
| SILK v3 container framing (`0x02` prefix, `#!SILK_V3`, length-prefixed frames, EOF) | ✅ done + tested |
| Native decode via vendored Skype SILK SDK | ✅ done + tested |
| PCM → WAV output | ✅ done + tested |
| Public API (`decode_to_pcm` / `decode_to_wav` / `parse_silk_container`) | ✅ done + tested |
| Bit-exact conformance vector (`vectors/`) | ✅ passing |

Verified end-to-end on real WeChat samples (e.g. a 2.00 s tone decodes to exactly 48000 samples
@ 24 kHz; a 20 KB speech note decodes to 7.54 s of audio).

## Usage

```python
from silk_decoder import decode_to_wav, decode_to_pcm, parse_silk_container

wav = decode_to_wav(data=open("voice.silk", "rb").read())    # complete WAV, ready for ffmpeg/transcription
pcm = decode_to_pcm(data=open("voice.silk", "rb").read())    # raw s16le mono PCM
info = parse_silk_container(data=open("voice.silk", "rb").read())  # framing/inspection only
```

Consumed as a library from `backend-service` — no CLI/subprocess.

## Layout

```
src/silk_decoder/
  container.py     WeChat/SILK v3 framing (ours, pure Python)
  wav.py           PCM -> WAV (ours)
  decoder.py       decode pipeline (container -> native -> WAV)
  _silkmodule.c    thin native wrapper around the vendored SDK (no DSP)
  errors.py        typed exceptions
vendor/silk/       vendored Skype SILK SDK reference sources (BSD-3-Clause) — see PROVENANCE.md
setup.py           builds the native extension from _silkmodule.c + vendor/silk/src/*.c
tests/             unit tests + tests/conformance/ (bit-exact vector gate)
vectors/           reference <name>.silk + <name>.pcm pairs
```

## Development

```
pip install -e ".[dev]"          # builds the native extension
pytest
# or, without installing (e.g. on a non-3.14 interpreter):
python setup.py build_ext --inplace && PYTHONPATH=src pytest
```

## CI

- **`ci.yml`** (push / PR): builds the extension, runs `ruff` + `pytest` on Python 3.14, and
  separately builds + installs the wheel and imports it — a release can't ship something that
  won't build or install.
- **`release.yml`** (on a `MAJOR.MINOR.PATCH` tag): checks the tag matches the `pyproject.toml`
  version, re-runs tests, builds, and publishes a GitHub Release with the sdist + wheel.

## Consuming it (backend-service)

First-party, **git-installed** — the same pattern `backend-service` already uses for
`msg-parser`. No PyPI. Add to `requirements/base.requirements.txt`:

```
silk-decoder @ git+https://github.com/closure-intel/silk-decoder.git@0.1.0  # WeChat SILK voice-note decoder
```

`uv pip install` builds the extension from the pinned tag at image-build time. backend-service's
worker image already has a C toolchain (it builds the Rust UFDR wheel), so this compiles there
too, and the repo access already set up for `msg-parser` covers this.

## Releasing

1. Bump `version` in `pyproject.toml`.
2. Tag and push: `git tag 0.2.0 && git push origin 0.2.0` (no `v` prefix, to match msg-parser).
3. `release.yml` verifies + tests + builds + publishes the GitHub Release.
4. Bump the pinned `@<version>` in backend-service's requirements.

## License

Our code is BSD-3-Clause (`LICENSE`). The vendored SILK SDK under `vendor/silk/` is
BSD-3-Clause © Skype Limited, with its original license headers retained — see
[`NOTICE`](NOTICE) and [`PROVENANCE.md`](PROVENANCE.md).
