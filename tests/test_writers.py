"""
Tests for ZoomzPeak Writers and Ingestion Utilities.
"""

import io
from pathlib import Path
import pyarrow.parquet as pq

from zoomzpeak.schema import conforms
from zoomzpeak.writers.zooms import (
    dataset_id_for,
    looks_like_peak_txt,
    rows_from_consolidated_csv,
    rows_from_txt_files,
    sanitize_id,
    write_zooms_dataset,
)


def test_id_sanitization():
    assert dataset_id_for("My Dataset 2026-09") == "My_Dataset_2026_09"
    assert sanitize_id("sample_001.txt") == "sample_001"
    assert sanitize_id("sample_001.TXT") == "sample_001"
    assert sanitize_id(Path("/path/to/spec_02.txt")) == "spec_02"


def test_looks_like_peak_txt():
    # Valid numeric 2-column text
    txt = "1000.5 5000\n1001.5 2000\n1002.5 3000\n"
    assert looks_like_peak_txt(io.StringIO(txt)) is True

    # Header / invalid text
    invalid_txt = "Some random words\nNot mass spec data\n"
    assert looks_like_peak_txt(io.StringIO(invalid_txt)) is False


def test_rows_from_consolidated_csv():
    csv_content = """filename,mz,intensity
sample1.txt,1200.5,500.0
sample1.txt,1500.2,800.0
sample2.txt,1100.1,250.0
"""
    rows = list(
        rows_from_consolidated_csv(
            csv_path_or_stream=io.StringIO(csv_content),
            dataset_id="Test_Dataset",
        )
    )
    assert len(rows) == 2
    assert rows[0]["file_id"] == "sample1.txt"
    assert len(rows[0]["mz"]) == 2
    assert rows[1]["file_id"] == "sample2.txt"
    assert len(rows[1]["mz"]) == 1


def test_rows_from_txt_files():
    txt_data = b"1200.5 500.0\n1500.2 800.0\n"
    txt_items = [("sample1.txt", txt_data)]
    rows = list(
        rows_from_txt_files(
            txt_items=txt_items,
            dataset_id="Test_Dataset",
        )
    )
    assert len(rows) == 1
    assert rows[0]["sample_id"] == "sample1"
    assert len(rows[0]["mz"]) == 2


def test_write_zooms_dataset(tmp_path):
    out_parquet = tmp_path / "spectra.parquet"
    test_rows = [
        {
            "file_id": "s1.txt",
            "dataset_id": "TestDS",
            "source_type": "external",
            "raw_path": "raw/s1.txt",
            "sample_id": "s1",
            "scan_number": 1,
            "rt": 0.0,
            "instrument": "MALDI-TOF",
            "mz": [1000.1, 1200.2],
            "intensity": [500.0, 1000.0],
            "n_peaks": 2,
            "is_centroided": True,
            "extraction_strategy": "txt_profile",
        }
    ]

    n_written = write_zooms_dataset(test_rows, out_parquet, dataset_id="TestDS")
    assert n_written == 1
    assert out_parquet.exists()

    # Verify table schema and conformance
    tbl = pq.read_table(out_parquet)
    ok, problems = conforms(tbl.schema, "zooms_spectra")
    assert ok is True, f"Written parquet failed conformance: {problems}"

    # Verify schema metadata
    meta = tbl.schema.metadata
    assert b"zoomzpeak.spec_version" in meta
    assert b"zoomzpeak.table_kind" in meta
    assert meta[b"zoomzpeak.table_kind"] == b"zooms_ms1_maldi_spectra"
