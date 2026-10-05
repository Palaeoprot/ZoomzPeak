"""
Precursor charge: how it is read, and what happens when it is absent.

Why this is its own module
--------------------------
Every legacy extractor resolved charge with one expression::

    charge = int(ms2_row.get("charge", 1)) or 1

That is a coercion, not a default. It turns "the reader did not report a charge" into
the positive assertion "this precursor is singly charged", and it does so silently, with
no column recording that a guess was made.

The consequences are measurable in the current store. Sampling 60 MS1 envelope files
(1.47M rows) on 2026-09-09: 91% of rows carry ``charge == 1`` and **56 of 60 files are
charge 1 on every single row**. An all-singly-charged LC-MS/MS DDA run is not physically
plausible -- tryptic peptides are predominantly 2+ and 3+. Those files did not measure
1+; they lost the charge state and had it invented for them.

It is not a cosmetic label, because the envelope window depends on it::

    hi = precursor_mz + N_ISOTOPES * ISOTOPE_SPACING / charge

A 2+ precursor coerced to 1+ gets a **+4.01 Da** window instead of **+2.01 Da** -- twice
as wide, admitting neighbouring isotope clusters and co-eluting species into what is
supposed to be one precursor's envelope. Anything downstream that reasons about envelope
purity, including FDR estimation, inherits that contamination without being told.

The rule this module enforces
-----------------------------
**Never invent a charge.** If the reader did not report one, the value is ``None`` and
``charge_source`` says ``unknown``. A window that cannot be computed honestly is not
computed: the row is either skipped or emitted flagged, at the caller's choice, but it
is never silently widened to the 1+ default.

False data is worse than absent data. Absent data is visible to the next person; a
fabricated 1+ is not.
"""

from __future__ import annotations

from typing import Optional

#: Da between isotope peaks of a singly charged ion (neutron mass difference).
ISOTOPE_SPACING = 1.00335
#: Isotope peaks captured above the precursor.
N_ISOTOPES = 4
#: Da captured below the precursor, to catch a mis-assigned monoisotopic peak.
LOW_OFFSET_DA = 1.5


class ChargeSource:
    """Provenance of the value in ``charge``."""

    #: Reported by the instrument/reader for this precursor.
    MEASURED = "measured"
    #: Not reported. ``charge`` is None. NOT a synonym for 1.
    UNKNOWN = "unknown"
    #: Present but outside a plausible range; retained here, not silently clamped.
    OUT_OF_RANGE = "out_of_range"

    ALL = (MEASURED, UNKNOWN, OUT_OF_RANGE)


#: Charges above this are almost always a mis-read rather than a real precursor in a
#: peptide DDA experiment. Flagged, never silently rewritten.
MAX_PLAUSIBLE_CHARGE = 8


def read_charge(raw_value) -> tuple[Optional[int], str]:
    """Interpret a reader's charge field.

    Returns ``(charge, charge_source)``. ``charge`` is ``None`` whenever the true value
    is not known -- including when the reader supplied 0, which universally means
    "undetermined" rather than "neutral".

    >>> read_charge(2)
    (2, 'measured')
    >>> read_charge(0)
    (None, 'unknown')
    >>> read_charge(None)
    (None, 'unknown')
    >>> read_charge(99)
    (99, 'out_of_range')
    """
    if raw_value is None:
        return None, ChargeSource.UNKNOWN
    try:
        c = int(raw_value)
    except (TypeError, ValueError):
        return None, ChargeSource.UNKNOWN
    if c <= 0:
        # 0 is the near-universal "undetermined" sentinel; negatives are negative-mode
        # or corrupt. Neither is evidence of a 1+ precursor.
        return None, ChargeSource.UNKNOWN
    if c > MAX_PLAUSIBLE_CHARGE:
        return c, ChargeSource.OUT_OF_RANGE
    return c, ChargeSource.MEASURED


def envelope_window(precursor_mz: float, charge: Optional[int]) -> Optional[tuple[float, float]]:
    """The m/z window to slice for this precursor's isotope envelope.

    Returns ``None`` when charge is unknown. That is deliberate and is the whole point of
    this module: the width is a function of charge, so without charge there is no correct
    window, and the 1+ window is a specific wrong answer rather than a neutral one.

    Callers decide what to do with ``None`` -- skip the row, or emit it with null
    envelope arrays and ``charge_source='unknown'`` so the gap stays countable.

    >>> envelope_window(500.0, 2)
    (498.5, 502.0067)
    >>> envelope_window(500.0, None) is None
    True
    """
    if charge is None or charge <= 0:
        return None
    lo = precursor_mz - LOW_OFFSET_DA
    hi = precursor_mz + N_ISOTOPES * ISOTOPE_SPACING / charge
    return lo, round(hi, 4)


def looks_flattened(charges) -> bool:
    """True if a run's charges are all 1 (or absent) -- the coercion signature.

    Used by ``validate`` to flag existing files written by the legacy extractors. It is a
    heuristic about a *run*, not a claim about any single spectrum: a genuine 1+ precursor
    is ordinary, a whole LC-MS/MS run of nothing but 1+ is not.
    """
    seen = {c for c in charges if c is not None}
    return seen <= {1}
