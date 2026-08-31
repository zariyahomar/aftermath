from aftermath.tools import compute_payoff, stacking_risk


def test_stacking_risk_levels():
    assert stacking_risk(20, 100)["level"] == "low"
    assert stacking_risk(50, 100)["level"] == "medium"
    assert stacking_risk(90, 100)["level"] == "high"
    assert stacking_risk(120, 100)["level"] == "critical"
    assert stacking_risk(10, 0)["level"] == "critical"


def test_compute_payoff_with_extra():
    none = compute_payoff(90, 30, 0)
    extra = compute_payoff(90, 30, 15)
    assert extra["periods"] < none["periods"]
    assert extra["periods"] == 2
