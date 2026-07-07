# Provenance of the vendored SILK SDK (`vendor/silk/`)

This package decodes SILK v3 using the **original Skype SILK SDK reference decoder**, vendored
into this repo rather than pulled from a PyPI wrapper. This file records exactly what was
vendored, from where, under what license, and how it's verified — so "we don't trust a random
repo" is backed by evidence, not assertion.

## What is vendored

- `vendor/silk/src/` — 110 `.c` + 24 `.h`: the Skype SILK SDK fixed-point codec sources.
- `vendor/silk/interface/` — 4 `.h`: the public SDK API (`SKP_Silk_SDK_API.h`, control struct, typedefs).
- Nothing else. The SDK's `test/` (its `main()` harnesses) is deliberately **not** vendored —
  our `src/silk_decoder/_silkmodule.c` replaces it.

## Source and license

- **Code origin:** the Skype SILK SDK. Obtained via the mirror
  `github.com/kn007/silk-v3-decoder`, path `silk/`, pinned at commit
  `507be6bca8ce1fb977a061481f1d79e8c610e309`. The mirror is only a delivery vehicle.
- **License:** **BSD-3-Clause, © 2006–2012 Skype Limited.** Every one of the 110 vendored `.c`
  files retains its original Skype BSD header (verified — see below). The mirror repo's
  root `LICENSE` is the mirror author's own MIT and does **not** govern the SDK files.
- **Why this source specifically:** standalone SILK v3 (what WeChat writes) can only be decoded
  by the original SDK. When SILK was integrated into Opus (RFC 6716) its entropy coder and
  framing changed, so xiph/opus's SILK cannot read a v3 stream.

## Verification

Done:
- **License integrity** — all 110 vendored `.c` files carry the `Copyright ... Skype Limited`
  BSD header; no header-less or foreign files were introduced.
- **Correctness** — the decoder reproduces expected audio on real WeChat samples: the committed
  conformance vector (`vectors/wechat_tone_2s_24k.silk`) decodes to exactly 48000 samples @
  24 kHz (2.00 s), and `tests/conformance/` asserts byte-for-byte reproduction.

Remaining before this is relied on in production (tracked in `ROADMAP.md`):
- **Independent cross-mirror byte-diff** — confirm `vendor/silk/src` is byte-identical to at
  least one *independent* SDK upload, so no single mirror could have tampered with it.
- **Static/security scan** — run Semgrep/CodeQL (C) over `vendor/silk/`.

## We do not use `pilk` / `pysilk`

No third-party SILK package is a dependency. The only third-party code is the vendored Skype
SDK above, pinned and license-clean.

## Updating the vendored SDK

Re-copy from a pinned upstream commit, update the commit hash above, and re-run the conformance
vectors + the security scan. Do not edit the vendored sources in place.
