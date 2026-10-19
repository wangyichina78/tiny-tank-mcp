"""Read-only lookups over the synthetic tank dataset in tank_data.py.

No network, no files, no enterprise systems. Each function returns facts only; deciding what
the facts mean (overdue, out of limits, inconsistent) is left to the calling agent.

Rejected input is never echoed back: it would carry caller-supplied text into the agent's context.
"""

import re
from typing import TypedDict

from src import tank_data

SOURCE = "Tiny Tank synthetic dataset (POC, not real data)"

TANK_ID_PATTERN = re.compile(r"TK-[0-9]{3}")
MAX_READING_DAYS = len(tank_data.READING_DATES)

RESULT_OK = "OK"
RESULT_NOT_FOUND = "NOT_FOUND"
RESULT_INVALID_INPUT = "INVALID_INPUT"

INVALID_TANK_ID_MESSAGE = "Tank ID must look like TK-### (for example TK-102). Ask the user for a valid ID."
INVALID_SITE_MESSAGE = "Site must be one of: " + ", ".join(tank_data.SITES) + ". Omit it to list all tanks."
INVALID_DAYS_MESSAGE = f"days must be a whole number from 1 to {MAX_READING_DAYS}."


class TankStatus(TypedDict):
    tank_id: str | None
    status: str | None
    site: str | None
    result_code: str
    message: str
    source: str


class TankSummary(TypedDict):
    tank_id: str
    site: str
    product: str
    capacity_bbl: int


class TankList(TypedDict):
    site: str | None
    count: int
    tanks: list[TankSummary]
    as_of: str
    result_code: str
    message: str
    source: str


class Inspection(TypedDict):
    date: str
    type: str
    result: str
    notes: str


class InspectionHistory(TypedDict):
    tank_id: str | None
    next_due: str | None
    inspections: list[Inspection]
    as_of: str
    result_code: str
    message: str
    source: str


class Reading(TypedDict):
    date: str
    level_pct: float
    temperature_f: float


class TankReadings(TypedDict):
    tank_id: str | None
    days: int | None
    high_alarm_pct: float | None
    low_alarm_pct: float | None
    readings: list[Reading]
    as_of: str
    result_code: str
    message: str
    source: str


def normalize_tank_id(raw: object) -> str:
    """Trim whitespace and upper-case. Non-strings become an empty string."""
    if not isinstance(raw, str):
        return ""
    return raw.strip().upper()


def _resolve_tank(raw_tank_id: object) -> tuple[str | None, str, str]:
    """Return (tank_id or None, result_code, message) for a raw ID."""
    tank_id = normalize_tank_id(raw_tank_id)
    if not TANK_ID_PATTERN.fullmatch(tank_id):
        return None, RESULT_INVALID_INPUT, INVALID_TANK_ID_MESSAGE
    if tank_id not in tank_data.TANKS:
        # Safe to echo: it matched the strict TK-### pattern.
        return tank_id, RESULT_NOT_FOUND, f"No tank with ID {tank_id} was found."
    return tank_id, RESULT_OK, ""


def lookup_tank(raw_tank_id: object) -> TankStatus:
    """Return the status and site for one tank ID, or a NOT_FOUND / INVALID_INPUT result."""
    tank_id, code, message = _resolve_tank(raw_tank_id)
    if code != RESULT_OK:
        return TankStatus(tank_id=tank_id, status=None, site=None, result_code=code, message=message, source=SOURCE)
    record = tank_data.TANKS[tank_id]
    return TankStatus(
        tank_id=tank_id,
        status=record["status"],
        site=record["site"],
        result_code=RESULT_OK,
        message=f"Tank {tank_id} at {record['site']} is {record['status']}.",
        source=SOURCE,
    )


def list_tanks(raw_site: object = None) -> TankList:
    """List all tanks, or the tanks at one site."""
    site = None
    if raw_site is not None:
        wanted = " ".join(raw_site.split()).casefold() if isinstance(raw_site, str) else ""
        site = next((s for s in tank_data.SITES if s.casefold() == wanted), None)
        if site is None:
            return TankList(site=None, count=0, tanks=[], as_of=tank_data.DATASET_AS_OF,
                            result_code=RESULT_INVALID_INPUT, message=INVALID_SITE_MESSAGE, source=SOURCE)
    tanks = [
        TankSummary(tank_id=tid, site=t["site"], product=t["product"], capacity_bbl=t["capacity_bbl"])
        for tid, t in tank_data.TANKS.items()
        if site is None or t["site"] == site
    ]
    scope = site or "all sites"
    return TankList(site=site, count=len(tanks), tanks=tanks, as_of=tank_data.DATASET_AS_OF,
                    result_code=RESULT_OK, message=f"{len(tanks)} tanks at {scope}.", source=SOURCE)


def inspection_history(raw_tank_id: object) -> InspectionHistory:
    """Return a tank's inspection records (newest first) and next due date."""
    tank_id, code, message = _resolve_tank(raw_tank_id)
    if code != RESULT_OK:
        return InspectionHistory(tank_id=tank_id, next_due=None, inspections=[], as_of=tank_data.DATASET_AS_OF,
                                 result_code=code, message=message, source=SOURCE)
    record = tank_data.INSPECTIONS[tank_id]
    inspections = [Inspection(**r) for r in record["records"]]
    return InspectionHistory(
        tank_id=tank_id,
        next_due=record["next_due"],
        inspections=inspections,
        as_of=tank_data.DATASET_AS_OF,
        result_code=RESULT_OK,
        message=f"{len(inspections)} inspection records for {tank_id}.",
        source=SOURCE,
    )


def tank_readings(raw_tank_id: object, days: object = MAX_READING_DAYS) -> TankReadings:
    """Return the last `days` daily readings (oldest first) and the tank's alarm limits."""
    tank_id, code, message = _resolve_tank(raw_tank_id)
    valid_days = isinstance(days, int) and not isinstance(days, bool) and 1 <= days <= MAX_READING_DAYS
    if code == RESULT_OK and not valid_days:
        code, message = RESULT_INVALID_INPUT, INVALID_DAYS_MESSAGE
    if code != RESULT_OK:
        return TankReadings(tank_id=tank_id, days=None, high_alarm_pct=None, low_alarm_pct=None, readings=[],
                            as_of=tank_data.DATASET_AS_OF, result_code=code, message=message, source=SOURCE)
    record = tank_data.READINGS[tank_id]
    pairs = list(zip(tank_data.READING_DATES, record["values"]))[-days:]
    readings = [Reading(date=d, level_pct=level, temperature_f=temp) for d, (level, temp) in pairs]
    return TankReadings(
        tank_id=tank_id,
        days=days,
        high_alarm_pct=record["high_alarm_pct"],
        low_alarm_pct=record["low_alarm_pct"],
        readings=readings,
        as_of=tank_data.DATASET_AS_OF,
        result_code=RESULT_OK,
        message=f"{days} daily readings for {tank_id}, level in percent of capacity.",
        source=SOURCE,
    )
