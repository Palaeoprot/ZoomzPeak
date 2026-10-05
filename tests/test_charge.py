"""
Tests for ZoomzPeak Precursor Charge Inference and Envelope Window Computation.
"""

from zoomzpeak.charge import (
    ChargeSource,
    envelope_window,
    looks_flattened,
    read_charge,
)


def test_read_charge_measured():
    c, src = read_charge(2)
    assert c == 2
    assert src == ChargeSource.MEASURED

    c, src = read_charge("3")
    assert c == 3
    assert src == ChargeSource.MEASURED


def test_read_charge_unknown_sentinels():
    # None
    c, src = read_charge(None)
    assert c is None
    assert src == ChargeSource.UNKNOWN

    # 0 (undetermined)
    c, src = read_charge(0)
    assert c is None
    assert src == ChargeSource.UNKNOWN

    # Negatives
    c, src = read_charge(-1)
    assert c is None
    assert src == ChargeSource.UNKNOWN

    # Non-numeric
    c, src = read_charge("invalid")
    assert c is None
    assert src == ChargeSource.UNKNOWN


def test_read_charge_out_of_range():
    c, src = read_charge(9)
    assert c == 9
    assert src == ChargeSource.OUT_OF_RANGE


def test_envelope_window():
    # Known charge 2+
    win = envelope_window(500.0, 2)
    assert win is not None
    lo, hi = win
    assert lo == 500.0 - 1.5
    assert abs(hi - (500.0 + 4 * 1.00335 / 2)) < 0.001

    # Unknown charge should return None (never fabricate 1+)
    assert envelope_window(500.0, None) is None
    assert envelope_window(500.0, 0) is None


def test_looks_flattened():
    assert looks_flattened([1, 1, 1, 1]) is True
    assert looks_flattened([1, None, 1]) is True
    assert looks_flattened([1, 2, 1, 3]) is False
