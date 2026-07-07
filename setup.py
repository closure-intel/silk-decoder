"""Build the native SILK decode extension.

Package metadata lives in pyproject.toml (PEP 621); only the C extension is declared
here. The extension compiles our thin wrapper (src/silk_decoder/_silkmodule.c) together
with the vendored Skype SILK SDK sources (vendor/silk/src/*.c). Built from source at
install time, so it targets whatever Python is installing it (3.14 in backend-service) —
no prebuilt-wheel/ABI mismatch, which was the whole problem with the existing packages.
"""

from pathlib import Path

from setuptools import Extension, setup

_SDK_SOURCES = sorted(str(p) for p in Path("vendor/silk/src").glob("*.c"))

silk_ext = Extension(
    name="silk_decoder._silk",
    sources=["src/silk_decoder/_silkmodule.c", *_SDK_SOURCES],
    include_dirs=["vendor/silk/interface", "vendor/silk/src"],
    # -w silences the vendored SDK's legacy warnings; we don't modify its source, so
    # there's nothing actionable to fix there and we don't want the noise in our build.
    extra_compile_args=["-O2", "-w"],
)

setup(ext_modules=[silk_ext])
