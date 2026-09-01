#!/usr/bin/env python3
"""Apply Gertius WIZ7 PSX English Patch V1.0 as the localization base.

This helper deliberately does not ship the upstream patch or game data. It
verifies the user-owned Japanese raw BIN and the separately supplied upstream
xdelta, applies it, and verifies the resulting English-base BIN. The Korean
full-disc builder can then use that English BIN with --allow-unverified-source,
so English menu/media/script fixes remain in place while Korean MSG/font/
scenario-name assets are layered on top.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
from pathlib import Path

SOURCE_MD5 = "188d3ee5a2a2242a719f290ea595e5ec"
UPSTREAM_XDELTA_SHA256 = "c689d37560dbe3cccc096d7fccfb288f0fc9edd0de9879557e048f42e580764a"
ENGLISH_BIN_MD5 = "7fb464147ab7144facae337226c91aa5"
ENGLISH_BIN_SHA256 = "6d61aaccf5a21853077f96b66e5fea4a2859611d89b5a93358e79d2f504c1683"


def file_hash(path: Path, algorithm: str) -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_xdelta(explicit: str | None) -> str:
    if explicit:
        p = Path(explicit)
        if p.is_file():
            return str(p.resolve())
        found = shutil.which(explicit)
        if found:
            return found
        raise ValueError(f"xdelta3 not found: {explicit}")
    found = shutil.which("xdelta3")
    if found:
        return found
    raise ValueError("xdelta3 not found; pass --xdelta3 /path/to/xdelta3")


def main() -> int:
    p = argparse.ArgumentParser(description="Prepare WIZ7 PSX English V1.0 base BIN")
    p.add_argument("source_bin", type=Path, help="verified Japanese raw BIN")
    p.add_argument("upstream_xdelta", type=Path, help="Gertius V1.0 Wiz7_patch.xdelta")
    p.add_argument("output_bin", type=Path, help="English-base BIN output")
    p.add_argument("--xdelta3", help="xdelta3 executable")
    args = p.parse_args()

    try:
        source = args.source_bin.resolve()
        patch = args.upstream_xdelta.resolve()
        output = args.output_bin.resolve()
        if not source.is_file():
            raise ValueError(f"source BIN not found: {source}")
        if not patch.is_file():
            raise ValueError(f"upstream xdelta not found: {patch}")

        source_md5 = file_hash(source, "md5")
        if source_md5 != SOURCE_MD5:
            raise ValueError(f"unsupported source BIN MD5: {source_md5}; expected {SOURCE_MD5}")

        patch_sha = file_hash(patch, "sha256")
        if patch_sha != UPSTREAM_XDELTA_SHA256:
            raise ValueError(
                f"unexpected upstream xdelta SHA256: {patch_sha}; expected {UPSTREAM_XDELTA_SHA256}"
            )

        xdelta3 = resolve_xdelta(args.xdelta3)
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            output.unlink()
        subprocess.run(
            [xdelta3, "-d", "-f", "-s", str(source), str(patch), str(output)],
            check=True,
        )

        out_md5 = file_hash(output, "md5")
        out_sha = file_hash(output, "sha256")
        if out_md5 != ENGLISH_BIN_MD5 or out_sha != ENGLISH_BIN_SHA256:
            output.unlink(missing_ok=True)
            raise ValueError(
                "English-base verification failed: "
                f"md5={out_md5} sha256={out_sha}"
            )

        print(f"source_md5={source_md5}")
        print(f"upstream_xdelta_sha256={patch_sha}")
        print(f"english_bin_md5={out_md5}")
        print(f"english_bin_sha256={out_sha}")
        print(f"output={output}")
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
