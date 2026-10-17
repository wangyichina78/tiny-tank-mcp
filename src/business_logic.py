"""Tank status lookup over a fixed set of synthetic records.

Read-only. No network, no files, no enterprise systems. The three tanks below are
made-up test data, not real operational data.
"""

import re
from typing import TypedDict

SOURCE = "Tiny Tank synthetic dataset (POC, not real data)"

TANK_ID_PATTERN = re.compile(r"TK-[0-9]{3}")

RESULT_OK = "OK"
RESULT_NOT_FOUND = "NOT_FOUND"
RESULT_INVALID_INPUT = "INVALID_INPUT"

_TANKS: dict[str, dict[str, str]] = {
    "TK-101": {"status": "In Service", "site": "Site A"},
    "TK-102": {"status": "Inspection Due", "site": "Site A"},
    "TK-103": {"status": "Out of Service", "site": "Site A"},
}


class TankStatus(TypedDict):
    tank_id: str | None
    status: str | None
    site: str | None
    result_code: str
    message: str
    source: str


def normalize_tank_id(raw: object) -> str:
    """Trim whitespace and upper-case. Non-strings become an empty string."""
    if not isinstance(raw, str):
        return ""
    return raw.strip().upper()


def lookup_tank(raw_tank_id: object) -> TankStatus:
    """Return the status and site for one tank ID, or a NOT_FOUND / INVALID_INPUT result."""
    tank_id = normalize_tank_id(raw_tank_id)

    if not TANK_ID_PATTERN.fullmatch(tank_id):
        # Never echo rejected input: it would carry caller-supplied text back into the agent's context.
        return TankStatus(
            tank_id=None,
            status=None,
            site=None,
            result_code=RESULT_INVALID_INPUT,
            message="Tank ID must look like TK-### (for example TK-102). Ask the user for a valid ID.",
            source=SOURCE,
        )

    record = _TANKS.get(tank_id)
    if record is None:
        return TankStatus(
            tank_id=tank_id,
            status=None,
            site=None,
            result_code=RESULT_NOT_FOUND,
            message=f"No tank with ID {tank_id} was found.",
            source=SOURCE,
        )

    return TankStatus(
        tank_id=tank_id,
        status=record["status"],
        site=record["site"],
        result_code=RESULT_OK,
        message=f"Tank {tank_id} at {record['site']} is {record['status']}.",
        source=SOURCE,
    )
