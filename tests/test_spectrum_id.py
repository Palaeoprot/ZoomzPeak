import numpy as np

from zoomzpeak.spectrum_id import spectrum_id


def test_matches_the_rust_reference_vectors():
    # Same vectors as zoomzpeak_schema::spectrum_id tests.
    assert spectrum_id("D20240599", "ZN0", [100.5, 200.25, 300.0], [10.0, 20.0, 30.0], scan=2) \
        == "D20240599_ZN0_s2_03388f"
    assert spectrum_id("D1", "raw_a", [], [], scan=7) == "D1_raw_a_s7_c3bd43"


def test_float32_arrays_and_lists_agree():
    mz = np.array([100.5, 200.25, 300.0], dtype=np.float32)
    it = np.array([10.0, 20.0, 30.0], dtype=np.float32)
    assert spectrum_id("D", "R", mz, it, scan=1) == spectrum_id("D", "R", list(mz), list(it), scan=1)


def test_changes_with_content_and_file():
    a = spectrum_id("D", "R", [1.0], [2.0], scan=1)
    assert a != spectrum_id("D", "R", [1.0], [2.5], scan=1)
    assert a != spectrum_id("D", "R2", [1.0], [2.0], scan=1)


def test_row_ordinal_marker():
    assert "_r4_" in spectrum_id("D", "R", [1.0], [2.0], row=4)
