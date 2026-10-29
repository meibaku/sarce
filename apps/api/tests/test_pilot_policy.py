from app.services.pilot_policy import CORE_STYLE_CAPABILITIES, EXPERIMENTAL_CAPABILITIES, PilotPolicy
from fastapi import HTTPException


def test_style_pilot_allows_only_core_style_surface():
    policy = PilotPolicy("style_v1")

    assert all(policy.allows(name) for name in CORE_STYLE_CAPABILITIES)
    assert not any(policy.allows(name) for name in EXPERIMENTAL_CAPABILITIES)
    assert policy.public()["experimentalHidden"] is True


def test_non_pilot_install_keeps_existing_product_surface():
    policy = PilotPolicy("off")

    assert all(policy.allows(name) for name in CORE_STYLE_CAPABILITIES | EXPERIMENTAL_CAPABILITIES)
    assert policy.public()["inviteOnly"] is False


def test_experimental_route_policy_fails_closed_and_home_is_filtered():
    policy = PilotPolicy("style_v1")
    try:
        policy.require("chaos")
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("experimental capability was admitted")

    filtered = policy.filter_home({"latest": {"chaos": [0.7], "highlight": 2}, "focus": {"trait": "Chaos"}, "stats": {"real": 1}})
    assert filtered == {"latest": {"chaos": [], "highlight": None}, "focus": None, "stats": None}


def test_core_review_strips_unvalidated_lens_content():
    policy = PilotPolicy("style_v1")
    review = policy.filter_review({"moments": [1], "ideas": [2], "closingOut": [3], "fightingBack": [4], "theirIdeas": [5]})
    assert review["moments"] == [1]
    assert review["ideas"] == review["closingOut"] == review["fightingBack"] == review["theirIdeas"] == []
    assert policy.filter_explanation({"brilliant": [1], "chaos": {"pFail": 0.5}}) == {"brilliant": [1], "chaos": None}


def test_pilot_explanation_explicitly_uses_nullable_chaos():
    filtered = PilotPolicy("style_v1").filter_explanation({"brilliant": [1], "chaos": {"verdict": "real_chaos"}})
    assert filtered["chaos"] is None
