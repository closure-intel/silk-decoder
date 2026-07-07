# ROADMAP — SILK signal-decode core

The container framing, WAV output, and API are done and tested. This document tracks the
remaining work: the SILK **signal decoder** itself, and how we make an in-house codec
trustworthy enough for forensic evidence.

## Guiding rule

A speech codec that "runs" but is subtly wrong produces audio that mis-transcribes — worse than
no decode at all in a case file. So **every stage is validated bit-exact against the reference
before we trust it**, and an unimplemented stage raises `SilkDecodeNotImplemented` rather than
emitting silence or garbage.

## Validation strategy (do this first)

1. **Obtain reference vectors as a development-time oracle.** For a set of real/synthetic
   `.silk` inputs, produce known-good signed-16-bit LE mono `.pcm` using the *reference* decoder
   (the RFC 6716 / Skype SILK reference), and commit `<name>.silk` + `<name>.pcm` pairs to
   `vectors/`. The reference is used **only** to generate oracle output at dev time — it is never
   a runtime dependency and never shipped.
2. `tests/conformance/` already compares our output to those pairs byte-for-byte. Green
   conformance on a representative corpus (multiple bitrates, VAD on/off, voiced/unvoiced,
   silence, max-length) is the definition of "done" for each stage.
3. This also answers the security question directly: correctness is proven against the
   published standard, not asserted.

## DSP stages (RFC 6716 §4 / Skype SILK SDK), each landed + vector-validated in order

1. **Range (entropy) decoder** — `icdf`-driven arithmetic decoding; the primitive every later
   stage reads through. Validate against hand-computed symbol sequences + a captured frame.
2. **Frame header** — VAD flags, LBRR flags, per-frame signal type & quantization offset type.
3. **Gains** — log-gain indices → linear quantized gains (with inter-frame delta coding).
4. **NLSF → LPC** — stage-1 codebook index + stage-2 residual, backward prediction,
   stabilization, and LSF→LPC conversion; plus LSF interpolation between subframes.
5. **LTP (voiced)** — pitch lag (primary + contour) and 5-tap LTP filter coefficient codebooks.
6. **Excitation** — shell coder: pulse counts/locations, LSBs, signs, and the LCG seed/dither.
7. **Synthesis + resample** — LTP and short-term (LPC) synthesis filters, gain application,
   subframe overlap/state carry, then resample from the SILK internal rate to the requested
   output rate (24 kHz for WeChat).

## Constant tables

SILK needs sizeable normative lookup tables (NLSF codebooks, pitch-contour tables, shell-coder
`icdf`s, etc.). These will be transcribed from the RFC/reference into `tables.py` and checked by
(a) shape/sum assertions and (b) the conformance vectors — a wrong table shows up immediately as
a vector mismatch.

## Performance

Pure Python is expected to be fine for the workload (voice notes are seconds long, decoded once
in the async worker pool). If profiling on real UFDR volumes shows it's too slow, the hot inner
loops (range decoder, LPC/LTP synthesis) are the candidates to move to a small Rust/Cython
extension later — the API and vectors stay identical, so that optimization is transparent.

## Integration (separate from this repo)

Once conformance is green, the Closure worker swaps its POC `pilk.decode(...)` call for a direct
import of this package inside `_decode_silk_to_pcm_wav` (`backend-service` is already Python 3.14,
and this package is pure Python, so it's a plain dependency — no subprocess); everything
downstream (WAV → ffmpeg → transcription/diarization) is unchanged and already proven.
