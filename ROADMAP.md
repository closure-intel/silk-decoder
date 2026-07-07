# ROADMAP

Decoding works and is verified: WeChat/SILK v3 → PCM/WAV via the vendored Skype SILK SDK, with a
bit-exact conformance vector, and the vendored source checked for provenance and safety
(see `PROVENANCE.md`). What's left is optional polish.

## Possible future work

- **More conformance vectors** — add `.silk`/`.pcm` pairs covering more cases (different bitrates,
  VAD on/off, longer notes, other SILK v3 sources like QQ) to widen the regression net.
- **Decoder-only slimming** — `vendor/silk/src` currently includes the SDK's encoder sources too
  (the SDK ships one tree; they compile but are unused). Could vendor decoder-only sources for a
  smaller build, after confirming exactly which files the decoder links and re-running conformance.
- **CodeQL C pass in CI** — Semgrep's OSS C coverage is thin; a CodeQL analysis would add deeper
  memory-safety checking if we want it.

## Non-issues

- **Performance** — native C; a multi-second note decodes in well under a second.
- **Python version** — pure-Python API + a from-source C extension, so it tracks whatever Python
  it's built against (3.14+).
