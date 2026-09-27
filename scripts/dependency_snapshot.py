"""Create a dependency snapshot from an installed build environment and vendored SDK."""

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import tarfile
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


def python_packages(project, inspection):
    installed = {canonicalize_name(p["metadata"]["name"]): p["metadata"] for p in inspection["installed"]}
    own_name = canonicalize_name(project["project"]["name"])
    environment = inspection["environment"]
    runtime = set()
    direct = set()
    edges = {name: set() for name in installed}

    def visit(requirements, is_runtime):
        pending = [(Requirement(r), {""}, None) for r in requirements]
        seen = set()
        while pending:
            req, parent_extras, parent = pending.pop()
            if req.marker and not any(req.marker.evaluate({**environment, "extra": e}) for e in parent_extras):
                continue
            name = canonicalize_name(req.name)
            if name not in installed:
                raise ValueError(f"Required package is missing from the build environment: {name}")
            if parent is None:
                direct.add(name)
            else:
                edges[parent].add(name)
            if is_runtime:
                runtime.add(name)
            extras = frozenset(req.extras | {""})
            if (name, extras) in seen:
                continue
            seen.add((name, extras))
            pending.extend((Requirement(r), extras, name) for r in installed[name].get("requires_dist", []))

    visit(project["project"].get("dependencies", []), True)
    visit(project["build-system"]["requires"], False)
    visit(project["project"].get("optional-dependencies", {}).get("dev", []), False)
    visit(["pip"], False)
    installed.pop(own_name, None)
    purls = {name: f"pkg:pypi/{name}@{quote(p['version'], safe='')}" for name, p in installed.items()}
    return {
        purls[name]: {
            "package_url": purls[name],
            "relationship": "direct" if name in direct else "indirect",
            "scope": "runtime" if name in runtime else "development",
            "dependencies": sorted(purls[child] for child in edges[name] if child in purls),
        }
        for name in sorted(installed)
    }


def verified_sdk(root):
    provenance = (root / "PROVENANCE.md").read_text()
    match = re.search(r"pinned at commit\s+`([0-9a-f]{40})`", provenance)
    if not match:
        raise ValueError("PROVENANCE.md must identify the vendored SDK commit")
    commit = match[1]
    with urlopen(f"https://codeload.github.com/kn007/silk-v3-decoder/tar.gz/{commit}", timeout=60) as response:
        archive = response.read()
    prefix = f"silk-v3-decoder-{commit}/silk/"
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        expected = {
            m.name.removeprefix(prefix): hashlib.sha256(tar.extractfile(m).read()).digest()
            for m in tar.getmembers()
            if m.isfile()
            and m.name.startswith((prefix + "src/", prefix + "interface/"))
            and m.name.endswith((".c", ".h"))
        }
    actual = {
        str(p.relative_to(root / "vendor/silk")): hashlib.sha256(p.read_bytes()).digest()
        for p in (root / "vendor/silk").rglob("*")
        if p.suffix in {".c", ".h"}
    }
    if not actual or actual != expected:
        raise ValueError("Vendored SDK files differ from the upstream commit in PROVENANCE.md")
    purl = f"pkg:github/kn007/silk-v3-decoder@{commit}#silk"
    return {
        purl: {
            "package_url": purl,
            "relationship": "direct",
            "scope": "runtime",
            "dependencies": [],
            "metadata": {"component": "Skype SILK SDK", "verified_files": len(actual)},
        }
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text())
    inspection = json.loads(subprocess.check_output([os.sys.executable, "-m", "pip", "inspect", "--local"]))
    repository = os.environ["GITHUB_REPOSITORY"]
    snapshot = {
        "version": 0,
        "sha": os.environ["GITHUB_SHA"],
        "ref": os.environ["GITHUB_REF"],
        "job": {
            "id": os.environ["GITHUB_RUN_ID"] + "-" + os.environ.get("GITHUB_RUN_ATTEMPT", "1"),
            "correlator": "silk-decoder-build-dependencies",
            "html_url": f"https://github.com/{repository}/actions/runs/{os.environ['GITHUB_RUN_ID']}",
        },
        "detector": {
            "name": "silk-decoder-dependencies",
            "version": "1.0.0",
            "url": f"https://github.com/{repository}/blob/{os.environ['GITHUB_SHA']}/scripts/dependency_snapshot.py",
        },
        "scanned": datetime.now(UTC).isoformat(),
        "manifests": {
            "pyproject.toml": {
                "name": "pyproject.toml",
                "file": {"source_location": "pyproject.toml"},
                "resolved": python_packages(project, inspection),
            },
            "vendor/silk": {
                "name": "vendor/silk",
                "file": {"source_location": "PROVENANCE.md"},
                "resolved": verified_sdk(root),
            },
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, indent=2) + "\n")


if __name__ == "__main__":
    main()
