"""
Recover true precursor charge from a Thermo .raw file.

Why this exists
---------------
``alpharaw.thermo.ThermoRawData.import_raw()`` produces a ``spectrum_df`` whose
``precursor_charge`` column is **0 for every scan** -- verified on
``PXD054549/2133_U.W.101-511_Etch_2b.raw``: 28,711 scans, all zero. The charge is not
missing from the file; the high-level import simply does not populate it.

The legacy writer then compounded that. ``universal_parquet_ingest.py:272`` reads::

    prec_charge = int(row["charge"]) if "charge" in row and not pd.isna(row["charge"]) else 1

alpharaw names the column ``precursor_charge``, not ``charge``, so the membership test is
False on every row and the ``else 1`` fires universally. Two independent faults, either
sufficient alone, both silent. Result: 3,642 of 6,280 MS2 files in the store (58%,
76.7M spectra) assert a charge of 1 that was never measured.

The same scans, read through the low-level reader:

    GetMS2MonoMzAndChargeFromScanNum()   2+ x1412, 3+ x775, 4+ x41, 5+ x11, 6+ x3
    trailer "Charge State"               2+ x1412, 3+ x775, 4+ x41, 5+ x11, 6+ x3

Identical, and a normal tryptic distribution. This module reads that.

Scan-number mapping
-------------------
alpharaw indexes spectra by ``spec_idx``; the Thermo API indexes by scan number. The
offset is almost always ``first_scan - 0``, but assuming it silently would mis-assign
every charge -- a worse failure than the one being fixed, because it would look
plausible. ``build_charge_map`` therefore verifies the mapping against ``precursor_mz``
and refuses to return a map it cannot corroborate.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

from zoomzpeak.charge import ChargeSource, read_charge

log = logging.getLogger(__name__)

#: Two precursor m/z values agreeing to within this are the same scan. Loose enough to
#: survive rounding between the two APIs, tight enough that an off-by-one lands outside.
MZ_TOLERANCE_DA = 0.01

#: Fraction of probe scans whose m/z must agree before the mapping is trusted.
MIN_AGREEMENT = 0.9

#: Minimum number of *usable* probes the agreement must be computed over. Filtering to
#: scans with a real precursor (below) can leave very few on a sparse file, and "100% of
#: 3 probes" is not verification -- it is a coin landing the same way three times.
MIN_PROBES = 20


def _usable_mz(value) -> bool:
    """True if a precursor m/z is a real measurement rather than a placeholder.

    Blanks, controls and washes carry many MS2 scans whose precursor m/z is 0.0 -- not
    None, so a `is None` test lets them through. Scoring the offset over those scans is
    what made the 90% gate refuse six blanks at 76-88% while their genuine precursors
    agreed perfectly. A scan with no real precursor is evidence about neither offset.
    """
    if value is None:
        return False
    try:
        return float(value) > 0.0
    except (TypeError, ValueError):
        return False


#: Isotope spacing (Da). The API returns the *monoisotopic* m/z while alpharaw's
#: spectrum_df carries the *selected* m/z, and when the instrument isolated a heavier
#: isotope the two differ by a whole number of these steps divided by the charge.
ISOTOPE_DA = 1.00335

#: Largest isotope offset treated as "same precursor". Instruments select at most a
#: couple of steps off monoisotopic; allowing more would start matching neighbours.
MAX_ISOTOPE_STEPS = 3


def _same_precursor(api_mz: float, df_mz: float) -> bool:
    """True if two m/z describe the same precursor, allowing an isotope offset.

    A straight equality test scored a stable 10-20% of scans on any real file as
    disagreements -- the API reports monoisotopic m/z, spectrum_df reports what was
    selected, and those differ by k * 1.00335 / z whenever a heavier isotope was
    isolated. That is what refused a genuine sample at 82% over 200 probes, after the
    blank-scoring fix had already been applied.

    This stays discriminating: a wrong scan offset yields an unrelated precursor, not
    one an isotope step away, so admitting these does not admit off-by-one mappings.
    """
    d = abs(api_mz - df_mz)
    if d <= MZ_TOLERANCE_DA:
        return True
    for z in range(1, 7):
        for k in range(1, MAX_ISOTOPE_STEPS + 1):
            if abs(d - k * ISOTOPE_DA / z) <= MZ_TOLERANCE_DA:
                return True
    return False


def score_offset(probe_rows, api_mz_for_scan, first: int, last: int, offset: int):
    """Agreement for one candidate offset. Returns (agreed, checked).

    Pure and reader-agnostic so the gate can be tested without a .raw file:
    `api_mz_for_scan(scan_number)` returns that scan's precursor m/z, or None.
    Only scans with a usable precursor m/z on *both* sides are counted.
    """
    checked = agreed = 0
    for _, row in probe_rows.iterrows():
        sn = int(row["spec_idx"]) + offset
        if sn < first or sn > last:
            continue
        df_mz = row.get("precursor_mz")
        if not _usable_mz(df_mz):
            continue
        try:
            api_mz = api_mz_for_scan(sn)
        except Exception:
            continue
        if not _usable_mz(api_mz):
            continue
        checked += 1
        if _same_precursor(float(api_mz), float(df_mz)):
            agreed += 1
    return agreed, checked


def _charge_for_scan(reader, scan_number: int) -> Tuple[Optional[int], str]:
    """Charge for one MS2 scan, preferring the API and falling back to the trailer."""
    try:
        _mz, z = reader.GetMS2MonoMzAndChargeFromScanNum(scan_number)
        c, src = read_charge(z)
        if c is not None:
            return c, src
    except Exception:
        pass
    try:
        trailer = reader.GetTrailerExtraForScanNum(scan_number)
        z2 = trailer.get("Charge State:", trailer.get("Charge State"))
        return read_charge(z2)
    except Exception:
        return None, ChargeSource.UNKNOWN


def build_charge_map(
    raw_path: str,
    spectrum_df,
    probe: int = 200,
) -> Dict[int, Tuple[Optional[int], str]]:
    """Map ``spec_idx`` -> ``(charge, charge_source)`` for the MS2 scans of one file.

    Returns an empty dict if the spec_idx -> scan_number correspondence cannot be
    verified, so a caller can fail loudly rather than write mis-assigned charges. An
    empty map means "unknown for every scan", which is honest; a wrong map is not.
    """
    from alpharaw.raw_access import pythermorawfilereader as ptr

    if "ms_level" in spectrum_df.columns:
        ms2 = spectrum_df[spectrum_df["ms_level"] == 2]
    else:
        ms2 = spectrum_df
    if ms2.empty:
        return {}

    reader = ptr.RawFileReader(str(raw_path))
    try:
        first = reader.GetFirstSpectrumNumber()
        last = reader.GetLastSpectrumNumber()

        # Do NOT compute the offset and hope. alpharaw's spec_idx is 0-based while Thermo
        # scan numbers are 1-based, but deriving that from (first - min(spec_idx)) is a
        # trap: taking the minimum over the MS2 subset rather than the whole frame gives
        # -3 on a file whose true offset is +1, and every charge would then be read off
        # the wrong scan. Search a small window and accept only an offset the data
        # corroborates.
        # Probe over scans that actually have a precursor. A sparse file needs more
        # rows inspected to reach MIN_PROBES usable ones, so widen the window rather
        # than score it on its blanks.
        probe_rows = ms2.head(max(probe, MIN_PROBES * 10))

        def _api_mz(scan_number):
            mz, _z = reader.GetMS2MonoMzAndChargeFromScanNum(scan_number)
            return mz

        best_off, best_ratio, best_checked = None, 0.0, 0
        for off in (1, 0, -1, 2, -2, 3, -3):
            agreed, checked = score_offset(probe_rows, _api_mz, first, last, off)
            ratio = (agreed / checked) if checked else 0.0
            if checked >= MIN_PROBES and ratio > best_ratio:
                best_off, best_ratio, best_checked = off, ratio, checked
            if checked >= MIN_PROBES and ratio >= MIN_AGREEMENT:
                break  # unambiguous; no need to try the rest

        if best_checked < MIN_PROBES:
            log.warning("%s: could not verify scan mapping (%d usable probes, need "
                        "%d -- too few scans carry a real precursor m/z); charge "
                        "left unknown", raw_path, best_checked, MIN_PROBES)
            return {}
        if best_ratio < MIN_AGREEMENT:
            log.warning("%s: scan mapping unverified (best offset %s at %.0f%% m/z "
                        "agreement over %d probes, need %.0f%%); charge left unknown "
                        "rather than guessed",
                        raw_path, best_off, 100 * best_ratio, best_checked,
                        100 * MIN_AGREEMENT)
            return {}

        log.info("%s: scan mapping offset %+d verified (%.0f%% of %d probes)",
                 raw_path, best_off, 100 * best_ratio, best_checked)

        out: Dict[int, Tuple[Optional[int], str]] = {}
        for spec_idx in ms2["spec_idx"].astype(int):
            out[int(spec_idx)] = _charge_for_scan(reader, int(spec_idx) + best_off)
        return out
    finally:
        try:
            reader.Close()
        except Exception:
            pass


def summarise(charge_map: Dict[int, Tuple[Optional[int], str]]) -> str:
    """One-line distribution, for logging a run without dumping every scan."""
    from collections import Counter

    c = Counter(v[0] for v in charge_map.values())
    if not c:
        return "no charges recovered"
    parts = [f"{k if k is not None else 'unknown'}+:{v}" for k, v in sorted(
        c.items(), key=lambda x: (x[0] is None, x[0]))]
    return " ".join(parts)
