"""Check scope classification and fail closed on incomplete dependency evidence."""

import importlib.util
import io
import tarfile
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "dependency_snapshot", Path(__file__).resolve().parents[1] / "scripts/dependency_snapshot.py"
)
snapshot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snapshot)


def test_runtime_extras_and_build_tools_have_distinct_scopes():
    project = {
        "project": {
            "name": "silk-decoder",
            "dependencies": ["runtime[feature]"],
            "optional-dependencies": {"dev": ["dev-tool"]},
        },
        "build-system": {"requires": ["setuptools"]},
    }
    packages = [
        ("silk-decoder", []),
        ("runtime", ['child; extra == "feature"', 'windows-only; sys_platform == "win32"']),
        ("child", []),
        ("setuptools", []),
        ("dev-tool", ["child"]),
        ("pip", []),
    ]
    inspection = {
        "environment": {"sys_platform": "linux"},
        "installed": [{"metadata": {"name": name, "version": "1.0", "requires_dist": deps}} for name, deps in packages],
    }
    actual = snapshot.python_packages(project, inspection)
    assert "pkg:pypi/silk-decoder@1.0" not in actual
    assert actual["pkg:pypi/runtime@1.0"]["dependencies"] == ["pkg:pypi/child@1.0"]
    assert actual["pkg:pypi/child@1.0"]["scope"] == "runtime"
    assert actual["pkg:pypi/child@1.0"]["relationship"] == "indirect"
    assert actual["pkg:pypi/setuptools@1.0"]["scope"] == "development"
    inspection["installed"] = [p for p in inspection["installed"] if p["metadata"]["name"] != "child"]
    with pytest.raises(ValueError, match="missing.*child"):
        snapshot.python_packages(project, inspection)


def test_sdk_without_pinned_provenance_is_rejected(tmp_path):
    (tmp_path / "PROVENANCE.md").write_text("No upstream commit")
    with pytest.raises(ValueError, match="must identify"):
        snapshot.verified_sdk(tmp_path)


def test_sdk_modified_or_missing_files_are_rejected(tmp_path, monkeypatch):
    commit = "a" * 40
    (tmp_path / "PROVENANCE.md").write_text(f"pinned at commit `{commit}`")
    sdk = tmp_path / "vendor/silk/src"
    sdk.mkdir(parents=True)
    (sdk / "decoder.c").write_bytes(b"original SDK source")
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w:gz") as tar:
        content = b"original SDK source"
        entry = tarfile.TarInfo(f"silk-v3-decoder-{commit}/silk/src/decoder.c")
        entry.size = len(content)
        tar.addfile(entry, io.BytesIO(content))
    monkeypatch.setattr(snapshot, "urlopen", lambda *args, **kwargs: io.BytesIO(archive.getvalue()))
    assert len(snapshot.verified_sdk(tmp_path)) == 1
    (sdk / "decoder.c").write_bytes(b"modified")
    with pytest.raises(ValueError, match="differ"):
        snapshot.verified_sdk(tmp_path)
    (sdk / "decoder.c").unlink()
    with pytest.raises(ValueError, match="differ"):
        snapshot.verified_sdk(tmp_path)
