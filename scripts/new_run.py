from __future__ import annotations

import argparse
import json
import urllib.request


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--phase", default="initial", choices=["initial", "mutated"])
    args = parser.parse_args()
    payload = json.dumps(
        {"run_id": args.run_id, "scenario_id": args.scenario, "phase": args.phase}
    ).encode()
    request = urllib.request.Request(
        "http://127.0.0.1:8741/approvaltrace/activate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        print(response.read().decode())


if __name__ == "__main__":
    main()
