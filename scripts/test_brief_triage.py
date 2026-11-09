#!/usr/bin/env python3
"""Regression tests: credible single-source official minutes must enter research triage."""
from briefs import research_priority_screen

def screen(years=(2029,)):
    return {"eligible_event_years": list(years), "status": "research_further",
            "approach_ready": False}

def org(**changes):
    value = {"evidence": [{
        "url": "https://example.org/board-minutes",
        "source": "Official association page (monitored)",
        "window_stage": "possible_pre_rfp",
        "cycle_decisions": [{"event_year": 2029, "stage": "possible_pre_rfp"}],
    }], "distinct_sources": 1, "commitment_flags": [],
             "window_stages": ["possible_pre_rfp"]}
    value.update(changes)
    return value

assert research_priority_screen(org(), screen())["bucket"] == "research-next"
assert research_priority_screen(org(), screen())["official_cycle_sources"] == 1
assert research_priority_screen(org(commitment_flags=["hotel already contracted"]), screen())["bucket"] == "conflict-check"
assert research_priority_screen(org(window_stages=["possible_pre_rfp", "host_bid_in_progress"]), screen())["bucket"] == "early-watch"
assert research_priority_screen(org(evidence=[]), screen())["bucket"] == "early-watch"
assert research_priority_screen(org(), screen(()))["bucket"] == "early-watch"
assert research_priority_screen(org(evidence=[{"url": "https://example.org/blog",
    "source": "Independent blog", "window_stage": "possible_pre_rfp",
    "cycle_decisions": [{"event_year": 2029}]}]), screen())["bucket"] == "early-watch"
print("Source-quality-first research triage regression tests passed.")
