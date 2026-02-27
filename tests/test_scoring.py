"""Test scoring functions."""

from src.analysis.daytrade_scorer import _score_rsi, _score_trend, score_to_grade


def test_score_to_grade_boundaries():
    assert score_to_grade(95) == "A+"
    assert score_to_grade(90) == "A+"
    assert score_to_grade(85) == "A"
    assert score_to_grade(70) == "B"
    assert score_to_grade(55) == "C"
    assert score_to_grade(40) == "D"
    assert score_to_grade(30) == "F"
    assert score_to_grade(0) == "F"


def test_rsi_sweet_spot():
    """RSI 30-50 should score highest (recovery zone)."""
    sweet = _score_rsi(35)
    high = _score_rsi(75)
    assert sweet > high


def test_rsi_none_returns_default():
    assert _score_rsi(None) == 40


def test_trend_mapping():
    assert _score_trend("bullish") == 100
    assert _score_trend("bearish") == 0
    assert _score_trend(None) == 40
    assert _score_trend("unknown") == 40
