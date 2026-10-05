"""
Tests for ZoomzPeak Schema Definitions and Conformance Auditing.
"""

from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from zoomzpeak.schema import (
    ADDED_IN_0_1_0,
    BY_NAME,
    InstrumentStatus,
    MS1_ENVELOPE,
    MS2_SPECTRA,
    SCHEMA_VERSION,
    ZOOMS_ENUMS,
    ZOOMS_SPECTRA,
    conforms,
    empty_table,
)


def test_schema_constants():
    assert SCHEMA_VERSION == "0.1.0"
    assert "zooms_spectra" in BY_NAME
    assert "ms2_spectra" in BY_NAME
    assert "ms1_envelope" in BY_NAME

    assert InstrumentStatus.FROM_HEADER == "from_header"
    assert len(InstrumentStatus.ALL) == 5
    assert len(InstrumentStatus.RESOLVED) == 2


def test_zooms_enums():
    assert "external" in ZOOMS_ENUMS["source_type"]
    assert "internal" in ZOOMS_ENUMS["source_type"]
    assert "txt_profile" in ZOOMS_ENUMS["extraction_strategy"]
    assert "mrt_summed_lockmass" in ZOOMS_ENUMS["extraction_strategy"]
    assert "fticr_centroid" in ZOOMS_ENUMS["extraction_strategy"]


def test_empty_table():
    tbl = empty_table("zooms_spectra")
    assert tbl.num_rows == 0
    assert tbl.schema.names == ZOOMS_SPECTRA.names

    with pytest.raises(KeyError):
        empty_table("non_existent_table")


def test_conforms_exact_match():
    ok, problems = conforms(ZOOMS_SPECTRA, "zooms_spectra")
    assert ok is True
    assert len(problems) == 0

    ok_ms2, problems_ms2 = conforms(MS2_SPECTRA, "ms2_spectra")
    assert ok_ms2 is True
    assert len(problems_ms2) == 0

    ok_env, problems_env = conforms(MS1_ENVELOPE, "ms1_envelope")
    assert ok_env is True
    assert len(problems_env) == 0


def test_conforms_upgradeable():
    # Schema without the 3 columns added in 0.1.0
    legacy_fields = [f for f in ZOOMS_SPECTRA if f.name not in ADDED_IN_0_1_0["zooms_spectra"]]
    legacy_schema = pa.schema(legacy_fields)

    ok, problems = conforms(legacy_schema, "zooms_spectra")
    assert ok is True  # Upgradeable is not fatal
    assert any("upgradeable" in p for p in problems)


def test_conforms_fatal_missing_column():
    bad_fields = [f for f in ZOOMS_SPECTRA if f.name != "mz"]
    bad_schema = pa.schema(bad_fields)

    ok, problems = conforms(bad_schema, "zooms_spectra")
    assert ok is False
    assert any("missing column 'mz'" in p for p in problems)


def test_conforms_fatal_wrong_type():
    fields = []
    for f in ZOOMS_SPECTRA:
        if f.name == "scan_number":
            fields.append(pa.field("scan_number", pa.string()))
        else:
            fields.append(f)
    bad_schema = pa.schema(fields)

    ok, problems = conforms(bad_schema, "zooms_spectra")
    assert ok is False
    assert any("scan_number" in p and "expected" in p for p in problems)


def test_conforms_extra_columns():
    fields = list(ZOOMS_SPECTRA) + [pa.field("custom_metadata_tag", pa.string())]
    extra_schema = pa.schema(fields)

    ok, problems = conforms(extra_schema, "zooms_spectra")
    assert ok is True  # Extra columns are non-fatal
    assert any("extra columns" in p for p in problems)


def test_fixture_parquet_conformance():
    fixture_path = Path(__file__).parent / "fixtures" / "example_zooms_spectra.parquet"
    if not fixture_path.exists():
        pytest.skip("Fixture example_zooms_spectra.parquet not found")

    table = pq.read_table(fixture_path)
    ok, problems = conforms(table.schema, "zooms_spectra")
    assert ok is True, f"Fixture failed schema conformance: {problems}"
