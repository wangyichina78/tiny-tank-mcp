"""Offline tests for the agent-eval scoring. No API key or network needed."""

from tools.agent_eval import extract, load_cases, score

CASES = {c["id"]: c for c in load_cases()}


def passed(checks):
    return all(c["pass"] for c in checks)


def test_ae01_cases_file_is_well_formed():
    known = {"id", "prompt", "expect_tool", "expect_ids", "must_contain", "contain_any",
             "must_not_contain", "cites_source", "judge"}
    assert len(CASES) == len(load_cases())
    for case in CASES.values():
        assert {"id", "prompt"} <= set(case) and set(case) <= known, case["id"]


def test_ae02_extract_reads_connector_blocks():
    blocks = [
        {"type": "thinking", "thinking": ""},
        {"type": "mcp_tool_use", "id": "t1", "name": "get_tank_status", "server_name": "tiny-tank",
         "input": {"tank_id": "tk-102"}},
        {"type": "mcp_tool_result", "tool_use_id": "t1", "is_error": False,
         "content": [{"type": "text", "text": "{}"}]},
        {"type": "text", "text": "TK-102 is Inspection Due."},
    ]
    ids, results, text = extract(blocks)
    assert ids == ["tk-102"] and len(results) == 1 and text == "TK-102 is Inspection Due."


def test_ae03_grounded_answer_passes():
    reply = "TK-102 at Site A is Inspection Due (source: Tiny Tank synthetic dataset)."
    assert passed(score(CASES["ok_basic"], ["TK-102"], reply))


def test_ae04_answer_without_tool_call_fails():
    checks = score(CASES["ok_basic"], [], "TK-102 is Inspection Due, per the synthetic dataset.")
    assert not passed(checks)
    assert [c["name"] for c in checks if not c["pass"]] == ["tool_called", "tool_args"]


def test_ae05_tool_args_normalized():
    assert passed(score(CASES["ok_lowercase"], [" tk-101 "], "TK-101 is In Service."))


def test_ae06_invented_status_on_not_found_fails():
    checks = score(CASES["not_found"], ["TK-999"], "TK-999 was not found, but it is probably In Service.")
    assert not passed(checks)


def test_ae07_off_topic_tool_call_fails():
    assert passed(score(CASES["off_topic"], [], "Paris."))
    assert not passed(score(CASES["off_topic"], ["TK-101"], "Paris."))


def test_ae08_multi_tank_needs_every_id():
    reply = "TK-101 is In Service; TK-103 is Out of Service."
    assert passed(score(CASES["multi_tank"], ["TK-101", "TK-103"], reply))
    assert not passed(score(CASES["multi_tank"], ["TK-101"], reply))


def test_ae09_judge_verdict_is_used():
    case = CASES["no_overreach"]
    reply = "TK-101 is In Service. That status alone doesn't tell you it's safe to fill."
    assert passed(score(case, ["TK-101"], reply, judge=lambda *a: (True, "PASS")))
    assert not passed(score(case, ["TK-101"], reply, judge=lambda *a: (False, "FAIL")))
    assert not passed(score(case, ["TK-101"], reply))  # judge case without a judge never passes
