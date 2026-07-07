# silk-decoder

Decode WeChat / Skype **SILK v3** (`.silk`) voice notes to PCM or WAV. A small pure-Python API
over a vendored copy of the reference SILK decoder — no third-party SILK packages.

## Why this exists

SILK v3 is the speech codec that later became the core of Opus. Two things make a dedicated
decoder necessary:

- **ffmpeg can't decode standalone SILK** — only SILK carried inside an Opus container.
- **Opus/xiph's SILK can't either** — its entropy coder and framing changed when SILK was folded
  into Opus, so the modern reference cannot read a v3 stream. Only the original Skype SILK SDK can.

The SILK packages on PyPI are thin, unmaintained wrappers around a mirrored copy of that SDK. This
package instead **vendors the Skype SILK SDK reference decoder (BSD-3-Clause) directly, builds it
from source, and wraps it thinly** — so the codec is owned in-tree and verifiable. See
[`PROVENANCE.md`](PROVENANCE.md) for what's vendored and how it's checked.

## How it works

```
container.py   parse SILK framing (0x02 prefix, #!SILK_V3, length-prefixed frames)   [pure Python]
   -> _silk    native wrapper drives the vendored Skype SILK SDK, frame -> PCM        [C, no DSP of ours]
   -> wav.py   wrap signed-16-bit mono PCM in a RIFF/WAV header                        [pure Python]
```

The only hand-written C is the ~150-line wrapper (`_silkmodule.c`); it implements no codec DSP.
The extension builds from source, so it works against whatever Python it's installed on (3.14+).

## Usage

```python
from silk_decoder import decode_to_wav, decode_to_pcm, parse_silk_container

wav  = decode_to_wav(data=open("voice.silk", "rb").read())          # complete WAV
pcm  = decode_to_pcm(data=open("voice.silk", "rb").read())          # raw s16le mono PCM
info = parse_silk_container(data=open("voice.silk", "rb").read())   # framing/inspection only
```

Defaults to 24 kHz mono (WeChat's rate); pass `sample_rate=` to override.

## Status

| Component | Status |
|---|---|
| SILK v3 container framing (`0x02` prefix, `#!SILK_V3`, length-prefixed frames, EOF) | ✅ tested |
| Native decode via vendored Skype SILK SDK | ✅ tested |
| PCM → WAV output | ✅ tested |
| Bit-exact conformance vector (`vectors/`) | ✅ passing |
| Provenance + security verification of the vendored SDK | ✅ see `PROVENANCE.md` |

Verified on real samples: a 2.00 s tone decodes to exactly 48000 samples @ 24 kHz; a 20 KB speech
note to 7.54 s of audio.

## Layout

```
src/silk_decoder/
  container.py     SILK v3 framing (pure Python)
  wav.py           PCM -> WAV
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
# or, on a non-3.14 interpreter (extension built in place):
python setup.py build_ext --inplace && PYTHONPATH=src pytest
```

CI (`.github/workflows/`) runs lint + tests and a from-source build on Python 3.14.

## License

This package's code is BSD-3-Clause (`LICENSE`). The vendored SILK SDK under `vendor/silk/` is
BSD-3-Clause © Skype Limited, with its original license headers retained — see [`NOTICE`](NOTICE)
and [`PROVENANCE.md`](PROVENANCE.md).
