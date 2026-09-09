"""
The pyarrow schemas for every table in the store.

Ported verbatim in field order and type from the three writers that previously each
owned their own copy:

  * ZOOMS_SPECTRA  <- ``MS1-Data/scripts/11_Export_MZPeak_Parquet_All.py`` (``SCHEMA``)
  * MS2_SPECTRA    <- ``MS2-Data/spectrum_extraction/universal_parquet_ingest.py``
  * MS1_ENVELOPE   <- ditto

Field names, order and types are unchanged, so parquet already in ``parquet_master``
stays readable and newly written files stay byte-compatible with the old writers.

Why the schemas live here rather than beside each writer
-------------------------------------------------------
The conformance audit's Finding 1 was that the ZooMS tree holds four different schemas.
That happens when each script carries its own literal. One definition, imported by every
writer and by the validator, is the structural fix.

PLAN.md §3 has ``schema.py`` eventually *generated from* ``vocab/*.cv.yaml`` so the CV
binding is the single source of truth. That inversion is not done yet: the vocabulary
files for ZooMS, MS2 and PSM do not exist. Until they do, this module is the source of
truth and ``vocab/`` is checked against it -- see ``validate.py``. When the vocabulary
lands, the dependency reverses and this module becomes generated output.

On nullability, and what a null actually means
----------------------------------------------
Every column here is nullable, which parquet allows and the old writers relied on. That
is not the same as every null meaning the same thing, and for ``instrument`` in
particular the difference matters:

  * **Not reported.** Most ZooMS submissions never state the instrument. The information
    does not exist anywhere in the deposit -- not in a header, not in the paper. No
    amount of better code recovers it; only a change in community reporting practice
    does.
  * **Not captured.** The source file *does* carry it and our writer discarded it. Two
    real instances, both now fixed: the ZooMS exporter hardcoded ``"instrument": None``
    for all four source strategies, and the LC-MS writer read alpharaw's ``.instrument``
    attribute, which returns the string ``"none"`` rather than the model.

Conflating the two makes the second look like the first and hides a bug behind a
community problem. ``ZOOMS_SPECTRA`` therefore carries ``instrument_status``, so a row
can say *which* kind of missing it is. See ``InstrumentStatus``.
"""

from __future__ import annotations

import pyarrow as pa

SCHEMA_VERSION = "0.1.0"


class InstrumentStatus:
    """Why ``instrument`` holds the value it does.

    Recorded per row so that "we do not know" and "nobody told us" stay distinguishable,
    and so a future backfill can find exactly the rows worth revisiting.
    """

    #: Model read from the vendor file header or an explicit, trustworthy declaration.
    FROM_HEADER = "from_header"
    #: Supplied out of band -- dataset sidecar, submission metadata, the paper.
    FROM_METADATA = "from_metadata"
    #: Source format carries no instrument field at all (peak-list CSV, plain text
    #: profile). Nothing was lost; there was nothing to read.
    NOT_IN_SOURCE = "not_in_source"
    #: The source could carry it, but this deposit does not state it. The common ZooMS
    #: case, and a community reporting gap rather than a software one.
    NOT_REPORTED = "not_reported"
    #: A header existed and the reader failed on it -- truncated file, unreadable
    #: trailer. Worth retrying; distinct from genuinely absent.
    READ_FAILED = "read_failed"

    ALL = (FROM_HEADER, FROM_METADATA, NOT_IN_SOURCE, NOT_REPORTED, READ_FAILED)

    #: Statuses where `instrument` is expected to be non-null.
    RESOLVED = (FROM_HEADER, FROM_METADATA)


# --------------------------------------------------------------------------- ZooMS MS1

#: MALDI-ToF ZooMS spectra: one row per spectrum, one spectrum per sample.
#:
#: ``rt`` is retained because the source formats emit it, but for MALDI it is a
#: file-format artefact and NOT elution time -- there is no chromatography and no time
#: axis. It must not be interpreted as retention time.
ZOOMS_SPECTRA = pa.schema(
    [
        ("file_id", pa.string()),
        ("dataset_id", pa.string()),
        ("source_type", pa.string()),
        ("raw_path", pa.string()),
        ("sample_id", pa.string()),
        ("scan_number", pa.int64()),
        ("rt", pa.float64()),
        ("instrument", pa.string()),
        ("mz", pa.list_(pa.float64())),
        ("intensity", pa.list_(pa.float64())),
        ("n_peaks", pa.int64()),
        ("is_centroided", pa.bool_()),
        ("extraction_strategy", pa.string()),
        # --- added in 0.1.0, nullable so existing files still conform ---
        ("instrument_status", pa.string()),
        ("instrument_serial", pa.string()),
        ("schema_version", pa.string()),
    ]
)

#: Closed vocabularies for the ZooMS enum columns, as observed in the store and
#: confirmed by the 2026-09-08 conformance audit. ``consolidated_csv`` is declared by
#: the legacy exporter but never produced any rows; it is kept because the code path
#: exists and may yet be exercised.
ZOOMS_ENUMS = {
    "source_type": {"external", "internal"},
    "extraction_strategy": {"consolidated_csv", "txt_profile", "mzxml_profile", "mzml_profile"},
    "instrument_status": set(InstrumentStatus.ALL),
}

# ------------------------------------------------------------------------ LC-MS/MS MS2

#: Fragment spectra. The only table a search engine can run on.
MS2_SPECTRA = pa.schema(
    [
        ("dataset_id", pa.string()),
        ("raw_filename", pa.string()),
        ("scan_number", pa.int64()),
        ("rt_seconds", pa.float64()),
        ("precursor_mz", pa.float64()),
        ("precursor_charge", pa.int32()),
        ("precursor_intensity", pa.float64()),
        ("n_peaks", pa.int32()),
        ("mz_array", pa.list_(pa.float32())),
        ("intensity_array", pa.list_(pa.float32())),
    ]
)

#: MS1 precursor envelopes: a narrow window around each MS2 precursor for mass-accuracy
#: QC. NOT full MS1 scans, and no substitute for MS2. Joined to MS2 via ``ms2_title``.
MS1_ENVELOPE = pa.schema(
    [
        ("file_id", pa.string()),
        ("pxd_accession", pa.string()),
        ("raw_path", pa.string()),
        ("ms2_title", pa.string()),
        ("ms2_rt", pa.float32()),
        ("precursor_mz", pa.float32()),
        ("charge", pa.int16()),
        ("ms1_scan_number", pa.int32()),
        ("ms1_rt", pa.float32()),
        ("envelope_mz", pa.list_(pa.float32())),
        ("envelope_intensity", pa.list_(pa.float32())),
        ("envelope_mobility", pa.list_(pa.float32())),
        ("has_ion_mobility", pa.bool_()),
        ("instrument", pa.string()),
    ]
)

BY_NAME = {
    "zooms_spectra": ZOOMS_SPECTRA,
    "ms2_spectra": MS2_SPECTRA,
    "ms1_envelope": MS1_ENVELOPE,
}


def empty_table(name: str) -> pa.Table:
    """An empty table with the named schema -- useful as a writer seed and in tests."""
    try:
        return BY_NAME[name].empty_table()
    except KeyError:
        raise KeyError(f"unknown schema {name!r}; known: {sorted(BY_NAME)}") from None


#: Columns introduced by ZoomzPeak 0.1.0 that the legacy writers never emitted. A file
#: without them is still conformant -- it predates them -- but is flagged as upgradeable.
#: Keeping this list explicit is what stops a schema addition from retrospectively
#: invalidating every file already in the store.
ADDED_IN_0_1_0 = {
    "zooms_spectra": {"instrument_status", "instrument_serial", "schema_version"},
    "ms2_spectra": set(),
    "ms1_envelope": set(),
}


def conforms(schema: pa.Schema, name: str) -> tuple[bool, list[str]]:
    """Compare a schema against the canonical one.

    Returns ``(ok, problems)``. Three outcomes are deliberately distinguished:

    * **fatal** -- a required column is absent, or present with the wrong type. Readers
      will break, so this fails.
    * **upgradeable** -- a column added in 0.1.0 is absent. The file predates the
      addition and every existing reader still works, so this does not fail.
    * **extra** -- columns we do not know about. Reported, never fatal; a downstream
      tool is entitled to add its own.
    """
    want = BY_NAME[name]
    added = ADDED_IN_0_1_0.get(name, set())
    problems: list[str] = []
    fatal = False
    have = {f.name: f.type for f in schema}

    for f in want:
        if f.name not in have:
            if f.name in added:
                problems.append(f"upgradeable: missing column {f.name!r} (added in 0.1.0)")
            else:
                problems.append(f"missing column {f.name!r}")
                fatal = True
        elif have[f.name] != f.type:
            problems.append(f"column {f.name!r} is {have[f.name]}, expected {f.type}")
            fatal = True

    extra = [n for n in have if n not in want.names]
    if extra:
        problems.append(f"extra columns (not an error): {sorted(extra)}")
    return (not fatal), problems
