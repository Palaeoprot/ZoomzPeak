"""
Generate the synthetic ZooMS example fixture.

The fixture mirrors the SHAPE of a real, richly-annotated ZooMS dataset -- the
Crafting Documents relic-label corpus (see fixtures/README.md) -- without
containing any of its measured data. Every spectrum here is generated from
published collagen peptide marker masses plus synthetic noise; no real
measurement, shelfmark, or species determination is reproduced.

Deterministic: same seed in, same bytes out.

    python tests/fixtures/make_fixture.py
"""

import hashlib
import random

import pyarrow as pa
import pyarrow.parquet as pq

from pathlib import Path

OUT = Path(__file__).parent / "example_zooms_spectra.parquet"

SPEC_VERSION = "mzPeakMS-ZooMS/0.1-draft"
DATASET_ID = "Smith_2023_Crafting_Documents"

# Published ZooMS collagen (COL1) peptide marker masses, [M+H]+.
# Sources: Buckley et al. 2009/2010, Kirby et al. 2013 and subsequent literature.
# These are reference values from the published record, not measurements.
MARKERS = {
    "Ovis aries": [1180.6, 1427.7, 1477.7, 1580.8, 2131.1, 2799.4, 2883.4, 3017.5, 3077.5],
    "Capra hircus": [1180.6, 1427.7, 1477.7, 1554.8, 2131.1, 2792.4, 2853.4, 3033.5, 3093.5],
    "Bos taurus": [1105.6, 1208.6, 1427.7, 1453.7, 1580.8, 2131.1, 2853.4, 3033.5, 3093.5],
}

# Synthetic samples. Identifiers are invented placeholders in an obviously
# fictional scheme -- deliberately NOT the real archival shelfmarks.
SAMPLES = [
    # sample_id,   collection,     provenance,                 taxon profile,  batch, plate
    ("EXAMPLE_001", "Collection A", "Example Abbey",            "Ovis aries",   "1", "0000000001"),
    ("EXAMPLE_002", "Collection A", "Example Abbey",            "Capra hircus", "1", "0000000001"),
    ("EXAMPLE_003", "Collection B", "Example Cathedral Treasury", "Bos taurus", "2", "0000000002"),
    ("EXAMPLE_004", "Collection B", "Example Cathedral Treasury", "Ovis aries", "2", "0000000002"),
    ("EXAMPLE_005", None,           None,                       "Ovis aries",   "3", None),
    ("EXAMPLE_006", "Collection C", "Example Monastic Library", "Capra hircus", "3", "0000000002"),
]

MZ_LO, MZ_HI = 800.0, 4000.0
N_NOISE = 28          # background peaks per spectrum
ISOTOPES = 3          # isotope peaks drawn per marker
C13 = 1.00336         # 13C-12C spacing


def make_spectrum(rng, taxon):
    """A synthetic centroided peak list: markers + isotopes + background."""
    mz, inten = [], []

    for m in MARKERS[taxon]:
        # jitter well under typical MALDI-ToF calibration error
        base = m + rng.gauss(0, 0.02)
        height = rng.uniform(2_000, 40_000)
        for i in range(ISOTOPES):
            mz.append(base + i * C13)
            # crude isotope envelope decay -- illustrative, not a real model
            inten.append(height * (0.62**i) * rng.uniform(0.9, 1.1))

    for _ in range(N_NOISE):
        mz.append(rng.uniform(MZ_LO, MZ_HI))
        inten.append(rng.uniform(80, 1_400))

    order = sorted(range(len(mz)), key=lambda i: mz[i])
    return (
        [round(mz[i], 4) for i in order],
        [round(inten[i], 1) for i in order],
    )


def main():
    rng = random.Random(20230201)  # project launch date, as a seed
    rows = []

    for sample_id, collection, provenance, taxon, batch, plate in SAMPLES:
        mz, inten = make_spectrum(rng, taxon)
        rows.append(
            {
                "file_id": f"{sample_id}.txt",
                "dataset_id": DATASET_ID,
                "source_type": "internal",
                "raw_path": f"example/{sample_id}.txt",
                "sample_id": sample_id,
                "collection_name": collection,
                "provenance": provenance,
                # Real datasets carry archival shelfmarks here. Withheld in the
                # fixture: a shelfmark identifies a specific extant document.
                "shelfmark": None,
                "plate": plate,
                "extraction_batch": batch,
                "instrument": "timsTOF fleX",
                "instrument_cv_id": "MS:1003005",
                "instrument_cv_label": "timsTOF fleX",
                "mz": mz,
                "intensity": inten,
                "n_peaks": len(mz),
                "n_scans_total": 3,
                "is_centroided": True,
            }
        )

    schema = pa.schema(
        [
            ("file_id", pa.string()),
            ("dataset_id", pa.string()),
            ("source_type", pa.string()),
            ("raw_path", pa.string()),
            ("sample_id", pa.string()),
            ("collection_name", pa.string()),
            ("provenance", pa.string()),
            ("shelfmark", pa.string()),
            ("plate", pa.string()),
            ("extraction_batch", pa.string()),
            ("instrument", pa.string()),
            ("instrument_cv_id", pa.string()),
            ("instrument_cv_label", pa.string()),
            ("mz", pa.list_(pa.float64())),
            ("intensity", pa.list_(pa.float64())),
            ("n_peaks", pa.int64()),
            ("n_scans_total", pa.int64()),
            ("is_centroided", pa.bool_()),
        ]
    )

    table = pa.Table.from_pylist(rows, schema=schema)

    # File-level metadata -- the block Finding 3 of the conformance audit says
    # every file should carry. Note it states plainly that this is synthetic.
    table = table.replace_schema_metadata(
        {
            "zoomzpeak.spec_version": SPEC_VERSION,
            "zoomzpeak.table_kind": "zooms_ms1_maldi_spectra",
            "zoomzpeak.builder": "tests/fixtures/make_fixture.py",
            "zoomzpeak.cv_reference": "PSI-MS",
            "zoomzpeak.content": "SYNTHETIC -- generated, not measured. Not research data.",
            "zoomzpeak.rng_seed": "20230201",
            "zoomzpeak.modelled_on": (
                "Crafting Documents (AHRC-DFG, 2023-), Oxford / BAM. "
                "Structure only; no measured data, shelfmarks or determinations."
            ),
        }
    )

    pq.write_table(table, OUT, compression="zstd", version="2.6")

    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
    print(f"wrote {OUT}  ({OUT.stat().st_size:,} bytes, {table.num_rows} rows)")
    print(f"sha256 {digest}")


if __name__ == "__main__":
    main()
