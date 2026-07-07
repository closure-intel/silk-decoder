"""Exception types for the SILK decoder.

Every failure mode is a distinct subclass of :class:`SilkError` so callers (and the
Closure worker that will wrap this package) can react precisely — e.g. treat a
truncated Cellebrite export differently from a genuinely malformed file.
"""


class SilkError(Exception):
    """Base class for every error this package raises."""


class InvalidSilkFile(SilkError):
    """The input is not a SILK v3 stream (missing/!bad ``#!SILK_V3`` magic)."""


class TruncatedSilkFile(SilkError):
    """A frame's declared length runs past the end of the data.

    Common with partial Cellebrite/UFDR exports — surfaced explicitly so the caller
    can decide whether to salvage the frames decoded so far or reject outright.
    """


class SilkDecodeNotImplemented(SilkError, NotImplementedError):
    """A SILK signal-decode stage that has not been implemented yet was reached.

    Container parsing and WAV output are complete and tested; the DSP core is being
    built and validated stage-by-stage against reference vectors (see ROADMAP.md).
    This is raised (rather than returning silence) so an unfinished stage can never be
    mistaken for a successful decode.
    """
