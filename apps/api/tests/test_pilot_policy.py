from app.services.pilot_policy import CORE_STYLE_CAPABILITIES, EXPERIMENTAL_CAPABILITIES, PilotPolicy


def test_style_pilot_allows_only_core_style_surface():
    policy = PilotPolicy("style_v1")

    assert all(policy.allows(name) for name in CORE_STYLE_CAPABILITIES)
    assert not any(policy.allows(name) for name in EXPERIMENTAL_CAPABILITIES)
    assert policy.public()["experimentalHidden"] is True


def test_non_pilot_install_keeps_existing_product_surface():
    policy = PilotPolicy("off")

    assert all(policy.allows(name) for name in CORE_STYLE_CAPABILITIES | EXPERIMENTAL_CAPABILITIES)
    assert policy.public()["inviteOnly"] is False
