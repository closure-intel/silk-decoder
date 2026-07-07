"""Top-level SILK decode pipeline: container -> per-frame signal decode -> PCM -> WAV.

The container framing (:mod:`silk_decoder.container`) and WAV output (:mod:`silk_decoder.wav`)
are complete and tested. The per-frame **signal decode** — the actual SILK DSP — is built and
validated stage-by-stage against reference test vectors (see ``ROADMAP.md`` and
``tests/conformance/``); until a stage lands it raises :class:`SilkDecodeNotImplemented` rather
than emitting anything that could be mistaken for a real decode.

The SILK decoder (RFC 6716 §4 / Skype SILK SDK) is a sequence of well-defined stages, each
independently testable against the reference:

    1. Range (entropy) decoder — read symbols from the arithmetic-coded bitstream.
    2. Frame header — VAD/LBRR flags, per-frame gains, signal type, quantization offset.
    3. NLSF decode — stage-1 vector-quantized codebook + stage-2 residual → LSF → LPC coeffs.
    4. Long-term prediction — pitch lags + 5-tap LTP filter coefficients (voiced frames).
    5. Excitation — shell-coded pulse locations, LSBs, signs, seed/dither (LCG).
    6. Synthesis — LTP + short-term (LPC) synthesis filters, gain application.
    7. Resample — SILK internal rate → requested output rate (24 kHz for WeChat).
"""

from silk_decoder.container import parse_silk_container
from silk_decoder.errors import SilkDecodeNotImplemented
from silk_decoder.wav import pcm_s16le_to_wav

#: WeChat voice notes are mono and the SILK bitstream carries no playback rate, so we decode
#: at WeChat's canonical rate. (Kept identical to the value proven in the Closure POC.)
DEFAULT_SAMPLE_RATE = 24000


class SilkFrameDecoder:
    """Stateful decoder for a single SILK stream (state persists across frames).

    Instantiated once per file; :meth:`decode_frame` is called for each container frame in
    order because inter-frame state (previous LPC/LTP, gains, resampler memory) carries over.
    """

    def __init__(self, *, sample_rate: int) -> None:
        """
        :param sample_rate: Target output sample rate in Hz.
        """
        self.sample_rate = sample_rate

    def decode_frame(self, *, payload: bytes) -> bytes:
        """Decode one SILK frame payload to signed-16-bit LE mono PCM.

        :param payload: One frame's raw SILK bitstream (from the container parser).
        :returns: Decoded PCM for this frame.
        :raises SilkDecodeNotImplemented: While the DSP core is still being built + validated.
        """
        raise SilkDecodeNotImplemented(
            "SILK signal decode is not implemented yet. Container parsing and WAV output are "
            "complete and tested; the DSP core is being implemented and validated bit-exact "
            "against reference vectors — see ROADMAP.md and tests/conformance/."
        )


def decode_to_pcm(*, data: bytes, sample_rate: int = DEFAULT_SAMPLE_RATE) -> bytes:
    """Decode a full SILK v3 file to raw signed-16-bit LE mono PCM.

    :param data: Raw ``.silk`` file bytes (with or without WeChat's ``0x02`` prefix).
    :param sample_rate: Target output rate in Hz.
    :returns: Concatenated PCM for every frame.
    """
    container = parse_silk_container(data=data)
    decoder = SilkFrameDecoder(sample_rate=sample_rate)
    pcm = bytearray()
    for frame in container.frames:
        pcm += decoder.decode_frame(payload=frame)
    return bytes(pcm)


def decode_to_wav(*, data: bytes, sample_rate: int = DEFAULT_SAMPLE_RATE) -> bytes:
    """Decode a full SILK v3 file straight to an in-memory WAV.

    :param data: Raw ``.silk`` file bytes.
    :param sample_rate: Target output rate in Hz.
    :returns: A complete WAV file (RIFF header + PCM).
    """
    return pcm_s16le_to_wav(pcm=decode_to_pcm(data=data, sample_rate=sample_rate), sample_rate=sample_rate)
