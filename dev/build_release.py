"""Build the installable HACS/Marketplace asset from the integration directory."""

import argparse
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components/sonos_follow_me"


def build_release(output: Path, tag: str | None = None):
    """Keep paths relative to the integration so both stores extract them correctly."""
    manifest = json.loads((INTEGRATION / "manifest.json").read_text())
    if tag is not None and tag != f"v{manifest['version']}":
        raise ValueError("Release tag must match manifest.json version")
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for source in sorted(INTEGRATION.rglob("*")):
            relative = source.relative_to(INTEGRATION)
            if any(part.startswith(".") or part == "__pycache__" for part in relative.parts):
                continue
            if source.is_symlink():
                raise ValueError(f"Unexpected symlink: {relative}")
            if not source.is_file() or source.suffix in {".pyc", ".pyo"}:
                continue
            if source.suffix not in {".py", ".json", ".js", ".png"}:
                raise ValueError(f"Unexpected integration file: {relative}")
            info = ZipInfo(relative.as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/sonos_follow_me.zip")
    parser.add_argument("--tag")
    args = parser.parse_args()
    print(build_release(args.output, args.tag))
