"""Compare two smoke-test evidence files (direct vs gateway) field by field (GT-05).

    python tools/compare_routes.py evidence/direct.json evidence/gateway.json

Exit 0 on parity, 1 on any difference.
"""

import json
import sys

def _key(call: dict) -> str:
    return f"{call.get('tool', 'get_tank_status')} {json.dumps(call['input'], sort_keys=True)}"


def compare(direct: dict, gateway: dict) -> list[str]:
    diffs = []
    d_calls = {_key(c): c for c in direct["calls"]}
    g_calls = {_key(c): c for c in gateway["calls"]}
    for key in sorted(d_calls.keys() | g_calls.keys()):
        if key not in d_calls or key not in g_calls:
            diffs.append(f"{key}: present on one route only")
            continue
        d, g = d_calls[key], g_calls[key]
        if d["is_error"] != g["is_error"]:
            diffs.append(f"{key}: is_error {d['is_error']} vs {g['is_error']}")
        dr, gr = d["result"] or {}, g["result"] or {}
        for field in sorted(dr.keys() | gr.keys()):
            if dr.get(field) != gr.get(field):
                diffs.append(f"{key}.{field}: {dr.get(field)!r} vs {gr.get(field)!r}")
    return diffs


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    with open(sys.argv[1]) as f:
        direct = json.load(f)
    with open(sys.argv[2]) as f:
        gateway = json.load(f)
    diffs = compare(direct, gateway)
    for line in diffs:
        print(f"[DIFF] {line}")
    print(f"Parity {'PASS' if not diffs else 'FAIL'} ({len(direct['calls'])} calls compared)")
    return 0 if not diffs else 1


if __name__ == "__main__":
    sys.exit(main())
