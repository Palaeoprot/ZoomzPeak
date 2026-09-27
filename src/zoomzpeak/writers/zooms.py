"""
ZoomzPeak Reference ZooMS Parquet Writer (mzPeakMS-ZooMS/0.1-draft).

This module is the canonical writer for ZooMS MALDI-ToF MS1 spectra tables,
enforcing the 16-column ``ZOOMS_SPECTRA`` schema, ZSTD compression, file-level
metadata stamping, and conformance auditing against ``zoomzpeak.schema``.
"""

from __future__ import annotations

import io
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pyteomics import mzml, mzxml

from zoomzpeak.schema import (
    InstrumentStatus,
    SCHEMA_VERSION,
    ZOOMS_ENUMS,
    ZOOMS_SPECTRA,
    conforms,
)

SPEC_VERSION = "mzPeakMS-ZooMS/0.1-draft"


def dataset_id_for(path_or_name: Path | str) -> str:
    """Derive a canonical dataset_id from a folder name or string."""
    name = path_or_name.name if isinstance(path_or_name, Path) else path_or_name
    return re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")


def sanitize_id(name: str) -> str:
    """Strip extension and normalize sample/file identifier."""
    stem = Path(name).stem
    return re.sub(r"\.txt$", "", stem, flags=re.IGNORECASE)


def looks_like_peak_txt(stream_or_path: Any) -> bool:
    """Sniff whether an input stream or file is a 2-column ASCII numeric peak list."""
    try:
        if isinstance(stream_or_path, (str, Path)):
            with open(stream_or_path, "r", encoding="utf-8", errors="replace") as f:
                return _sniff_lines(f)
        elif hasattr(stream_or_path, "read"):
            pos = stream_or_path.tell() if hasattr(stream_or_path, "tell") else None
            chunk = stream_or_path.read(1024)
            if pos is not None and hasattr(stream_or_path, "seek"):
                stream_or_path.seek(pos)
            text = chunk.decode("utf-8", errors="replace") if isinstance(chunk, bytes) else chunk
            lines = io.StringIO(text)
            return _sniff_lines(lines)
    except Exception:
        return False
    return False


def _sniff_lines(f: Iterator[str]) -> bool:
    count = 0
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = re.split(r"[\s,;\t]+", line)
        if len(parts) < 2:
            return False
        try:
            float(parts[0])
            float(parts[1])
            count += 1
        except ValueError:
            return False
        if count >= 3:
            return True
    return count > 0


# --------------------------------------------------------------------------- Extractors


def rows_from_consolidated_csv(
    csv_path_or_stream: Any,
    dataset_id: str,
    source_type: str = "external",
    raw_path_str: str | None = None,
    instrument: str | None = None,
    instrument_status: str = InstrumentStatus.NOT_IN_SOURCE,
    instrument_serial: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield spectrum records from a consolidated/pre-picked CSV file."""
    if isinstance(csv_path_or_stream, (str, Path)):
        df = pd.read_csv(csv_path_or_stream, encoding="utf-8", encoding_errors="replace")
        raw_path = str(csv_path_or_stream) if raw_path_str is None else raw_path_str
    else:
        df = pd.read_csv(csv_path_or_stream, encoding="utf-8", encoding_errors="replace")
        raw_path = raw_path_str or f"{dataset_id}_consolidated.csv"

    col_map = {c.strip().lower(): c for c in df.columns}
    fname_col = col_map.get("filename") or col_map.get("file") or col_map.get("spectrum")
    mz_col = col_map.get("mz") or col_map.get("m/z") or col_map.get("m_z") or col_map.get("mass")
    inten_col = col_map.get("intensity") or col_map.get("i") or col_map.get("int") or col_map.get("height")

    if not fname_col or not mz_col or not inten_col:
        return

    df = df[df[fname_col].notna()]
    df = df[~df[fname_col].astype(str).str.fullmatch(r"(?i)nan(\.txt)?")]

    for fname, grp in df.groupby(fname_col):
        mz_vals = [float(x) for x in grp[mz_col].dropna()]
        inten_vals = [float(x) for x in grp[inten_col].dropna()]
        if not mz_vals:
            continue
        yield {
            "file_id": str(fname),
            "dataset_id": dataset_id,
            "source_type": source_type,
            "raw_path": raw_path,
            "sample_id": sanitize_id(str(fname)),
            "scan_number": None,
            "rt": None,
            "instrument": instrument,
            "mz": mz_vals,
            "intensity": inten_vals,
            "n_peaks": len(mz_vals),
            "is_centroided": True,
            "extraction_strategy": "consolidated_csv",
            "instrument_status": instrument_status,
            "instrument_serial": instrument_serial,
            "schema_version": SCHEMA_VERSION,
        }


def rows_from_per_sample_csv(
    csv_items: Sequence[tuple[str, Any]],
    dataset_id: str,
    source_type: str = "external",
    instrument: str | None = None,
    instrument_status: str = InstrumentStatus.NOT_IN_SOURCE,
    instrument_serial: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield records from a collection of per-sample CSV peak lists."""
    for file_id, source in csv_items:
        try:
            if isinstance(source, bytes):
                f = io.BytesIO(source)
            elif isinstance(source, (str, Path)):
                f = open(source, "rb")
            else:
                f = source

            content = f.read()
            if isinstance(source, (str, Path)):
                f.close()

            lines = content.decode("utf-8", errors="replace").splitlines()
            if not lines:
                continue

            delim = ";" if ";" in lines[0] else ","
            start_line = 0
            for idx, line in enumerate(lines[:10]):
                line_str = line.strip()
                if not line_str or line_str.startswith("#") or line_str.startswith("-"):
                    continue
                parts = line_str.split(delim)
                if len(parts) >= 2:
                    try:
                        float(parts[0].strip())
                        float(parts[1].strip())
                        start_line = idx
                        break
                    except ValueError:
                        start_line = idx + 1

            valid_lines = [l for l in lines[start_line:] if l.strip() and not l.startswith("#")]
            if not valid_lines:
                continue

            mzs, intens = [], []
            for l in valid_lines:
                parts = re.split(r"[,;\s\t]+", l.strip())
                if len(parts) >= 2:
                    try:
                        m = float(parts[0])
                        i = float(parts[1])
                        mzs.append(m)
                        intens.append(i)
                    except ValueError:
                        continue

            if not mzs:
                continue

            yield {
                "file_id": Path(file_id).name,
                "dataset_id": dataset_id,
                "source_type": source_type,
                "raw_path": str(file_id),
                "sample_id": sanitize_id(Path(file_id).name),
                "scan_number": None,
                "rt": None,
                "instrument": instrument,
                "mz": mzs,
                "intensity": intens,
                "n_peaks": len(mzs),
                "is_centroided": True,
                "extraction_strategy": "consolidated_csv",
                "instrument_status": instrument_status,
                "instrument_serial": instrument_serial,
                "schema_version": SCHEMA_VERSION,
            }
        except Exception as e:
            print(f"  [zoomzpeak.writers.zooms] Warning: failed to parse CSV {file_id}: {e}", file=sys.stderr)


def rows_from_txt_files(
    txt_items: Sequence[tuple[str, Any]],
    dataset_id: str,
    source_type: str = "external",
    instrument: str | None = None,
    instrument_status: str = InstrumentStatus.NOT_REPORTED,
    instrument_serial: str | None = None,
    sample_id_map: dict[str, str] | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield records from 2-column ASCII peak/profile files."""
    for file_id, source in txt_items:
        try:
            if isinstance(source, bytes):
                stream = io.BytesIO(source)
            elif isinstance(source, (str, Path)):
                stream = open(source, "r", encoding="utf-8", errors="replace")
            else:
                stream = source

            arr = pd.read_csv(
                stream,
                sep=r"[\s,;\t]+",
                header=None,
                names=["mz", "intensity"],
                engine="python",
                encoding="utf-8" if not isinstance(source, bytes) else None,
                encoding_errors="replace" if not isinstance(source, bytes) else None,
                comment="#",
            )
            if isinstance(source, (str, Path)):
                stream.close()

            if arr.empty:
                continue

            arr["mz"] = pd.to_numeric(arr["mz"], errors="coerce")
            arr["intensity"] = pd.to_numeric(arr["intensity"], errors="coerce")
            arr = arr.dropna()
            if arr.empty:
                continue

            mz_list = arr["mz"].astype(float).tolist()
            inten_list = arr["intensity"].astype(float).tolist()

            fname = Path(file_id).name
            sample_id = sample_id_map.get(fname, sanitize_id(fname)) if sample_id_map else sanitize_id(fname)

            yield {
                "file_id": fname,
                "dataset_id": dataset_id,
                "source_type": source_type,
                "raw_path": str(file_id),
                "sample_id": sample_id,
                "scan_number": None,
                "rt": None,
                "instrument": instrument,
                "mz": mz_list,
                "intensity": inten_list,
                "n_peaks": len(mz_list),
                "is_centroided": False,
                "extraction_strategy": "txt_profile",
                "instrument_status": instrument_status,
                "instrument_serial": instrument_serial,
                "schema_version": SCHEMA_VERSION,
            }
        except Exception as e:
            print(f"  [zoomzpeak.writers.zooms] Warning: failed to parse TXT {file_id}: {e}", file=sys.stderr)


def rows_from_mzxml(
    mzxml_items: Sequence[tuple[str, Any]],
    dataset_id: str,
    source_type: str = "external",
    instrument: str | None = None,
    instrument_status: str = InstrumentStatus.NOT_REPORTED,
    instrument_serial: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield MS1 scan records from mzXML files or streams."""
    for file_id, source in mzxml_items:
        try:
            src = str(source) if isinstance(source, Path) else source
            with mzxml.read(src) as reader:
                for scan in reader:
                    if str(scan.get("msLevel")) != "1":
                        continue
                    mz = scan.get("m/z array")
                    inten = scan.get("intensity array")
                    if mz is None or len(mz) == 0:
                        continue
                    fname = Path(file_id).name
                    yield {
                        "file_id": fname,
                        "dataset_id": dataset_id,
                        "source_type": source_type,
                        "raw_path": str(file_id),
                        "sample_id": sanitize_id(fname),
                        "scan_number": int(scan.get("num", -1)) if scan.get("num") is not None else None,
                        "rt": float(scan.get("retentionTime")) if scan.get("retentionTime") is not None else None,
                        "instrument": instrument,
                        "mz": [float(x) for x in mz],
                        "intensity": [float(x) for x in inten],
                        "n_peaks": len(mz),
                        "is_centroided": False,
                        "extraction_strategy": "mzxml_profile",
                        "instrument_status": instrument_status,
                        "instrument_serial": instrument_serial,
                        "schema_version": SCHEMA_VERSION,
                    }
        except Exception as e:
            print(f"  [zoomzpeak.writers.zooms] Warning: failed to parse mzXML {file_id}: {e}", file=sys.stderr)


def rows_from_mzml(
    mzml_items: Sequence[tuple[str, Any]],
    dataset_id: str,
    source_type: str = "external",
    instrument: str | None = None,
    instrument_status: str = InstrumentStatus.NOT_REPORTED,
    instrument_serial: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield MS1 scan records from mzML files or streams."""
    for file_id, source in mzml_items:
        try:
            src = str(source) if isinstance(source, Path) else source
            with mzml.read(src) as reader:
                for scan in reader:
                    if scan.get("ms level") != 1:
                        continue
                    mz = scan.get("m/z array")
                    inten = scan.get("intensity array")
                    if mz is None or len(mz) == 0:
                        continue
                    rt = None
                    scan_list = scan.get("scanList", {}).get("scan", [{}])
                    if scan_list:
                        rt_val = scan_list[0].get("scan start time")
                        rt = float(rt_val) if rt_val is not None else None

                    inst = instrument
                    inst_status = instrument_status
                    if not inst:
                        inst_cfg = scan.get("instrumentConfigurationRef")
                        if inst_cfg:
                            inst = str(inst_cfg)
                            inst_status = InstrumentStatus.FROM_HEADER

                    fname = Path(file_id).name
                    spot_id = scan.get("spotID")
                    sample_id = f"{sanitize_id(fname)}_{spot_id}" if spot_id else sanitize_id(fname)

                    yield {
                        "file_id": fname,
                        "dataset_id": dataset_id,
                        "source_type": source_type,
                        "raw_path": str(file_id),
                        "sample_id": sample_id,
                        "scan_number": int(scan.get("index", 0)) if scan.get("index") is not None else None,
                        "rt": rt,
                        "instrument": inst,
                        "mz": [float(x) for x in mz],
                        "intensity": [float(x) for x in inten],
                        "n_peaks": len(mz),
                        "is_centroided": False,
                        "extraction_strategy": "mzml_profile",
                        "instrument_status": inst_status,
                        "instrument_serial": instrument_serial,
                        "schema_version": SCHEMA_VERSION,
                    }
        except Exception as e:
            print(f"  [zoomzpeak.writers.zooms] Warning: failed to parse mzML {file_id}: {e}", file=sys.stderr)


# ----------------------------------------------------------------------------- Writer


def write_zooms_dataset(
    rows: Iterable[dict[str, Any]],
    out_path: Path,
    dataset_id: str,
    extra_metadata: dict[str, str] | None = None,
    batch_size: int = 50,
) -> int:
    """Write an iterable of ZooMS spectrum records to Parquet with full ZoomzPeak metadata."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    schema = ZOOMS_SPECTRA

    meta = {
        "zoomzpeak.spec_version": SPEC_VERSION,
        "zoomzpeak.table_kind": "zooms_ms1_maldi_spectra",
        "zoomzpeak.builder": "zoomzpeak.writers.zooms",
        "zoomzpeak.cv_reference": "PSI-MS",
        "zoomzpeak.schema_version": SCHEMA_VERSION,
        "zoomzpeak.dataset_id": dataset_id,
        "zoomzpeak.created_utc": datetime.now(timezone.utc).isoformat(),
    }
    if extra_metadata:
        meta.update(extra_metadata)

    schema_with_meta = schema.with_metadata(meta)

    writer = None
    batch = []
    total = 0

    try:
        for row in rows:
            if row.get("dataset_id") != dataset_id:
                row["dataset_id"] = dataset_id
            if "schema_version" not in row or not row["schema_version"]:
                row["schema_version"] = SCHEMA_VERSION

            st = row.get("source_type")
            if st and st not in ZOOMS_ENUMS["source_type"]:
                row["source_type"] = "external"

            strat = row.get("extraction_strategy")
            if strat and strat not in ZOOMS_ENUMS["extraction_strategy"]:
                row["extraction_strategy"] = "consolidated_csv"

            status = row.get("instrument_status")
            if not status or status not in ZOOMS_ENUMS["instrument_status"]:
                row["instrument_status"] = (
                    InstrumentStatus.FROM_METADATA if row.get("instrument") else InstrumentStatus.NOT_REPORTED
                )

            batch.append(row)
            if len(batch) >= batch_size:
                table = pa.Table.from_pylist(batch, schema=schema).replace_schema_metadata(meta)
                if writer is None:
                    writer = pq.ParquetWriter(
                        out_path,
                        schema_with_meta,
                        compression="zstd",
                        version="2.6",
                    )
                writer.write_table(table)
                total += len(batch)
                batch = []

        if batch:
            table = pa.Table.from_pylist(batch, schema=schema).replace_schema_metadata(meta)
            if writer is None:
                writer = pq.ParquetWriter(
                    out_path,
                    schema_with_meta,
                    compression="zstd",
                    version="2.6",
                )
            writer.write_table(table)
            total += len(batch)
    finally:
        if writer is not None:
            writer.close()

    if total > 0:
        written_schema = pq.read_schema(out_path)
        ok, problems = conforms(written_schema, "zooms_spectra")
        if not ok:
            print(f"  [zoomzpeak.writers.zooms] Conformance ERROR for {dataset_id}: {problems}", file=sys.stderr)

    return total


def write_sidecar(
    dataset_id: str,
    out_dir: Path,
    parquet_path: Path,
    metadata_overrides: dict[str, Any] | None = None,
) -> Path:
    """Generate or update the experiments_metadata/<dataset_id>.json sidecar."""
    out_dir.mkdir(parents=True, exist_ok=True)
    sidecar_path = out_dir / f"{dataset_id}.json"

    table = pq.read_table(parquet_path)
    df = table.select(
        ["file_id", "sample_id", "instrument", "source_type", "extraction_strategy"]
    ).to_pandas()

    instruments = sorted(df["instrument"].dropna().unique().tolist())
    source_types = sorted(df["source_type"].dropna().unique().tolist())
    strategies = sorted(df["extraction_strategy"].dropna().unique().tolist())

    sidecar_data = {
        "dataset_id": dataset_id,
        "n_files": int(df["file_id"].nunique()),
        "n_spectra_rows": int(len(df)),
        "n_unique_samples": int(df["sample_id"].nunique()),
        "instrument": instruments,
        "source_type": source_types,
        "extraction_strategy": strategies,
        "_metadata_source": {
            "n_files": "derived_from_parquet",
            "n_spectra_rows": "derived_from_parquet",
            "instrument": "from_metadata" if instruments else None,
        },
        "citation": None,
        "species": None,
        "sample_provenance": None,
        "_enrichment_note": (
            "citation/species/sample_provenance intentionally left blank -- these need "
            "the actual publication looked up per dataset_id, not guessed from the folder "
            "name. Fill in from the source paper before treating this sidecar as complete."
        ),
    }

    if metadata_overrides:
        sidecar_data.update(metadata_overrides)

    sidecar_path.write_text(json.dumps(sidecar_data, indent=2), encoding="utf-8")
    return sidecar_path
