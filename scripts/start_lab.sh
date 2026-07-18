#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p .approvaltrace
python -m approvaltrace.cli capture-api --root .approvaltrace
