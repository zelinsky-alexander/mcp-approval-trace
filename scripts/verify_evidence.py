from __future__ import annotations

import argparse
from pathlib import Path

from approvaltrace.evidence.manifest import verify_manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    errors = verify_manifest(args.run_dir)
    if errors:
        raise SystemExit("\n".join(errors))
    print("PASS: evidence bundle hashes are valid")


if __name__ == "__main__":
    main()
