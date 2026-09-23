import pytest

from pulsemetrics.experiments import analyze


def test_significant_practical_lift_recommends_ship():
    result = analyze(214, 1000, 280, 1000, practical_threshold=0.03)
    assert result.absolute_lift == pytest.approx(0.066)
    assert result.ci_low > 0
    assert result.p_value < 0.05
    assert result.recommendation.startswith("Ship")
    assert 0 < result.mde_absolute < 1
    assert 0 < result.design_power < 1


def test_inconclusive_result_does_not_claim_significance():
    result = analyze(21, 100, 22, 100)
    assert result.ci_low < 0 < result.ci_high
    assert result.recommendation.startswith("Continue")


def test_invalid_counts_rejected():
    with pytest.raises(ValueError):
        analyze(11, 10, 2, 10)
