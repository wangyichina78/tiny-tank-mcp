"""Synthetic tank dataset: a fixed snapshot, not real operational data.

Two records are deliberately inconsistent so an agent has something to find by combining tools:
- TK-105 is "In Service", but its inspection is overdue and its level is above the high alarm.
- TK-107 is "Out of Service", but its level is rising.
"""

DATASET_AS_OF = "2026-10-16"

READING_DATES = [
    "2026-10-10",
    "2026-10-11",
    "2026-10-12",
    "2026-10-13",
    "2026-10-14",
    "2026-10-15",
    "2026-10-16",
]

SITES = ("Site A", "Site B")

TANKS: dict[str, dict] = {
    "TK-101": {"site": "Site A", "product": "Gasoline", "capacity_bbl": 80000, "status": "In Service"},
    "TK-102": {"site": "Site A", "product": "Diesel", "capacity_bbl": 100000, "status": "Inspection Due"},
    "TK-103": {"site": "Site A", "product": "Jet Fuel", "capacity_bbl": 60000, "status": "Out of Service"},
    "TK-104": {"site": "Site A", "product": "Crude Oil", "capacity_bbl": 250000, "status": "In Service"},
    "TK-105": {"site": "Site B", "product": "Diesel", "capacity_bbl": 120000, "status": "In Service"},
    "TK-106": {"site": "Site B", "product": "Gasoline", "capacity_bbl": 80000, "status": "In Service"},
    "TK-107": {"site": "Site B", "product": "Jet Fuel", "capacity_bbl": 60000, "status": "Out of Service"},
    "TK-108": {"site": "Site B", "product": "Crude Oil", "capacity_bbl": 250000, "status": "In Service"},
}

# Newest first. next_due is None while a tank is out of service awaiting repair.
INSPECTIONS: dict[str, dict] = {
    "TK-101": {
        "next_due": "2027-03-12",
        "records": [
            {"date": "2022-03-12", "type": "External", "result": "Pass", "notes": "No findings."},
            {"date": "2017-03-09", "type": "Internal", "result": "Pass", "notes": "Minor floor pitting, within limits."},
        ],
    },
    "TK-102": {
        "next_due": "2026-10-25",
        "records": [
            {"date": "2021-10-25", "type": "External", "result": "Pass", "notes": "Paint touch-up recommended."},
        ],
    },
    "TK-103": {
        "next_due": None,
        "records": [
            {"date": "2026-08-02", "type": "Internal", "result": "Fail",
             "notes": "Floor corrosion beyond limits. Repair required before return to service."},
            {"date": "2021-07-30", "type": "External", "result": "Pass", "notes": "No findings."},
        ],
    },
    "TK-104": {
        "next_due": "2028-05-20",
        "records": [
            {"date": "2023-05-20", "type": "Internal", "result": "Pass", "notes": "No findings."},
        ],
    },
    "TK-105": {
        "next_due": "2026-09-30",
        "records": [
            {"date": "2021-09-30", "type": "External", "result": "Pass", "notes": "No findings."},
        ],
    },
    "TK-106": {
        "next_due": "2028-01-15",
        "records": [
            {"date": "2023-01-15", "type": "External", "result": "Pass", "notes": "No findings."},
        ],
    },
    "TK-107": {
        "next_due": None,
        "records": [
            {"date": "2026-09-15", "type": "Internal", "result": "Fail",
             "notes": "Floating roof seal failure. Tank removed from service pending repair."},
        ],
    },
    "TK-108": {
        "next_due": "2027-11-02",
        "records": [
            {"date": "2022-11-02", "type": "External", "result": "Pass", "notes": "No findings."},
        ],
    },
}

# Daily readings for READING_DATES, oldest first: (level percent of capacity, temperature F).
READINGS: dict[str, dict] = {
    "TK-101": {"high_alarm_pct": 90.0, "low_alarm_pct": 10.0,
               "values": [(58.2, 71.0), (60.1, 70.4), (61.7, 69.8), (59.4, 70.2), (57.0, 71.1), (55.8, 71.5), (56.9, 70.9)]},
    "TK-102": {"high_alarm_pct": 90.0, "low_alarm_pct": 10.0,
               "values": [(70.3, 68.2), (71.0, 68.0), (69.6, 67.7), (68.9, 68.4), (70.2, 68.9), (71.4, 69.1), (70.8, 68.6)]},
    "TK-103": {"high_alarm_pct": 90.0, "low_alarm_pct": 10.0,
               "values": [(0.4, 66.0), (0.4, 65.8), (0.3, 65.5), (0.3, 65.9), (0.3, 66.2), (0.2, 66.4), (0.2, 66.1)]},
    "TK-104": {"high_alarm_pct": 92.0, "low_alarm_pct": 8.0,
               "values": [(44.6, 79.3), (43.1, 79.0), (41.8, 78.6), (40.2, 78.9), (42.5, 79.4), (45.0, 79.8), (46.3, 79.5)]},
    "TK-105": {"high_alarm_pct": 90.0, "low_alarm_pct": 10.0,
               "values": [(88.5, 69.0), (89.4, 69.3), (90.6, 69.1), (91.8, 69.6), (92.9, 69.8), (93.7, 70.1), (94.6, 70.0)]},
    "TK-106": {"high_alarm_pct": 90.0, "low_alarm_pct": 10.0,
               "values": [(30.4, 72.2), (27.1, 72.0), (24.0, 71.6), (20.8, 71.9), (17.5, 72.3), (14.9, 72.6), (12.5, 72.4)]},
    "TK-107": {"high_alarm_pct": 90.0, "low_alarm_pct": 10.0,
               "values": [(0.5, 65.1), (5.1, 65.4), (11.8, 65.9), (18.4, 66.3), (24.9, 66.0), (31.2, 66.5), (37.6, 66.8)]},
    "TK-108": {"high_alarm_pct": 92.0, "low_alarm_pct": 8.0,
               "values": [(61.0, 80.1), (61.4, 80.4), (60.7, 80.0), (60.2, 79.7), (61.9, 80.3), (62.3, 80.6), (62.0, 80.2)]},
}
