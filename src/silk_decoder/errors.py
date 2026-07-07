"""Exception types for the SILK decoder.

Every failure mode is a distinct subclass of :class:`SilkError` so callers (and the
Closure worker that will wrap this package) can react precisely — e.g. treat a truncated
Cellebrite export differently from a genuinely malformed file.
"""


class SilkError(Exception):
    """Base class for every error this package raises."""


class InvalidSilkFile(SilkError):
    """The input is not a SILK v3 stream (missing/bad ``#!SILK_V3`` magic)."""


class TruncatedSilkFile(SilkError):
    """A frame's declared length runs past the end of the data.

    Common with partial Cellebrite/UFDR exports — surfaced explicitly so the caller can
    decide whether to salvage the frames decoded so far or reject outright.
    """


class SilkDecodeError(SilkError):
    """The native SILK decoder returned an error, or the native extension is not built."""
