# ROADMAP

Decoding works today: WeChat/SILK v3 → PCM/WAV via the vendored Skype SILK SDK, exercised by a
bit-exact conformance vector. What remains is hardening and integration.

## Provenance hardening (before production reliance)

- **Independent cross-mirror byte-diff** of `vendor/silk/src` against at least one other SDK
  upload, to prove no single mirror tampered with it. (First alternate mirror tried was gone;
  pick another SDK source and diff.)
- **Static/security scan** (Semgrep / CodeQL C) over `vendor/silk/`, recorded in the PR.

See `PROVENANCE.md` for what's already verified (license headers intact; correct decode).

## Optional slimming

`vendor/silk/src` currently includes the SDK's encoder sources too (the SDK ships one tree).
They're harmless and compiled-but-unused. If we want a smaller build we can vendor decoder-only
sources — but only after establishing which files the decoder links, and re-running conformance.

## Coverage

The decoder is source-agnostic: any SILK v3 stream decodes, so QQ/other SILK v3 voice works too,
not just WeChat. Add more conformance vectors (different bitrates, VAD on/off, longer notes) as we
encounter them.

## Performance

Native C; a multi-second voice note decodes in well under a second. If profiling on real UFDR
volumes ever shows a bottleneck, it's already in C — no action expected.

## Integration (in backend-service, separate repo)

Swap the POC's `pilk.decode(...)` in `_decode_silk_to_pcm_wav` for a direct import of this
package (`silk_decoder.decode_to_wav`), and drop the `pilk` dependency. Everything downstream
(WAV → ffmpeg → transcription/diarization) is unchanged and already proven.
