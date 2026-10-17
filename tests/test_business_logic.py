from src.business_logic import (
    RESULT_INVALID_INPUT,
    RESULT_NOT_FOUND,
    RESULT_OK,
    SOURCE,
    lookup_tank,
)

FIELDS = {"tank_id", "status", "site", "result_code", "message", "source"}


def test_ut01_tk101_in_service():
    r = lookup_tank("TK-101")
    assert (r["result_code"], r["status"], r["site"]) == (RESULT_OK, "In Service", "Site A")


def test_ut02_tk102_inspection_due():
    r = lookup_tank("TK-102")
    assert (r["result_code"], r["status"], r["site"]) == (RESULT_OK, "Inspection Due", "Site A")


def test_ut03_tk103_out_of_service():
    r = lookup_tank("TK-103")
    assert (r["result_code"], r["status"], r["site"]) == (RESULT_OK, "Out of Service", "Site A")


def test_ut04_unknown_valid_id_not_found():
    r = lookup_tank("TK-999")
    assert r["result_code"] == RESULT_NOT_FOUND
    assert r["status"] is None and r["site"] is None


def test_ut05_wrong_format_invalid():
    for bad in ("TANK-102", "TK102", "TK-1022", "", "   ", None, 102):
        assert lookup_tank(bad)["result_code"] == RESULT_INVALID_INPUT, bad


def test_ut06_normalizes_case_and_whitespace():
    r = lookup_tank("  tk-102 ")
    assert r["tank_id"] == "TK-102" and r["result_code"] == RESULT_OK


def test_ut07_every_result_has_same_fields_and_source():
    for tank_id in ("TK-101", "TK-999", "TANK-102"):
        r = lookup_tank(tank_id)
        assert set(r) == FIELDS
        assert r["source"] == SOURCE
