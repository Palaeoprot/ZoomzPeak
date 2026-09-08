---
type: doc
status: active
tags: [conformance, audit, parquet, schema, thermal-age, psi-ms, mzpeak, zooms]
relatedTo: [zoomzpeak, parquet-master, thermal-age]
---

# Conformance audit of `parquet_master`
**Date & Time:** 2026-09-08 (+02:00)

A pre-publication check of the existing Parquet estate against the conformance
levels in [`PLAN.md`](../PLAN.md) §4.3. Read against the estate as it stands today,
before any migration.

**Headline: nothing currently reaches L1, and the ZooMS side does not yet reach
L0.** That is expected — the levels were defined to measure this gap — but two of
the findings are real data problems rather than missing metadata, and one is a
genuine unlock.

| Table family | Files | Schemas found | Level |
|---|---|---|---|
| ZooMS MS1 (MALDI) | 29 | **4** | **fails L0** |
| LC-MS/MS MS2 fragment | 6,002 | 1 | **L0** |
| LC-MS/MS MS1 envelope | 6,062 | 1 | **L0** |
| ZooMS picked peaks | 28 | 2 | L0 (informal) |
| in-silico libraries | 30 | 1 | L0 (informal) |
| PSM results | 1,032 | 15 | not assessed — downstream |

---

## Finding 1 — the ZooMS tree holds four different schemas (blocks L0)

The specification assumes one. Of 29 dataset files:

**26 files — the canonical 13-column schema.** These are fine.
`file_id, dataset_id, source_type, raw_path, sample_id, scan_number, rt,
instrument, mz, intensity, n_peaks, is_centroided, extraction_strategy`

**1 file — `Collins_2026_Rabin/spectra.parquet`, 16 columns.** Written by the
bespoke exporter (`10_Export_MZPeak_Parquet.py`) rather than the generalised one,
and the two have silently diverged:

- *Missing*: `scan_number`, `rt`, `extraction_strategy`
- *Extra*: `collection_name`, `provenance`, `shelfmark`, `plate`,
  `extraction_batch`, `n_scans_total`

The extra columns are **not junk** — `shelfmark`, `collection_name` and
`provenance` are exactly the kind of L2 context the rest of the estate lacks. This
is the one dataset where the archaeological half was done properly, and the schema
divergence is the reason it could not be generalised. That argues for promoting
these into the shared schema rather than stripping them to match.

**2 files that are not ZooMS spectra at all**, sitting in the `dataset_id=`
partition tree where a spectra table is expected:

| File | Rows | Problem |
|---|---|---|
| `Parchment_QE_Values_24K/picked_peaks.parquet` | 52,502,834 | **One row per peak, not per spectrum.** Columns `spectrum_id, mz, intensity, snr, prominence`. This is a *picked-peaks* product — the `picked/` tree's format — filed in the raw spectra tree. |
| `Parchment_QE_Values_All/test_spectra_sample.parquet` | 934 | A **test sample** file. Different column names for the same concepts (`mz_array`/`intensity_array` vs `mz`/`intensity`), plus `mz_min, mz_max, n_points, tic`. |

These two dominate the row count: of 52,517,213 rows in the tree, **52,503,768
(99.97%) are in these two non-conforming files**. Any query that globs
`dataset_id=*/*.parquet` and assumes the 13-column schema is reading mostly
non-conforming rows, and a per-peak table silently unioned with a per-spectrum
table produces nonsense at 3,900× the row count.

### Resolved 2026-09-08 — with a correction

Both files were moved to
`ZooMS_parquet/zooms_ms1_maldi/_quarantine_2026-09-08/` (nothing deleted; the
directory name deliberately falls outside the `dataset_id=*` glob). The tree now
reads **27 files, 13,445 rows, 2 schemas** — 26 canonical plus Rabin.

Two corrections to what this section originally said:

1. **`picked_peaks.parquet` did not need moving to `picked/` — it was already
   there.** The copy in the spectra tree was a **byte-identical duplicate** of
   `picked/dataset_id=Parchment_QE_Values_24K/picked_peaks.parquet`, verified by
   full-file SHA256 (`69546b9e…c29d1d`), matching row count, row-group count and
   size. It was a leftover copy, not a misfiling, so it was quarantined for
   deletion rather than relocated.

2. **A third, undocumented spectra format was missed by this audit.**
   `dataset_id=Parchment_QE_Values_24K/chunks/` holds **24 files, 29.5 GB,
   19,945 real profile spectra** in the same schema as the quarantined test
   sample (`spectrum_id, project_folder, filename, mz_min, mz_max, n_points,
   tic, mz_array, intensity_array`). The original audit's glob
   (`dataset_id=*/*.parquet`) does not descend one level, so these never appeared.

   They are **left in place** — they are genuine data, and they do not break the
   documented glob. But a *recursive* glob returns 51 files rather than 27, so
   anything reading the tree recursively sees a schema the specification does not
   define. Converting them to the canonical schema (or defining a documented
   profile-spectra variant) is real follow-up work, not cleanup.

   The wider lesson for the validator: **it must walk recursively.** A
   single-level glob is exactly how these stayed invisible.

**Still recommended:** make the writer refuse to emit a file whose schema does not
match, and have the validator report unexpected files rather than skipping them.

## Finding 2 — `instrument` is null in 99% of ZooMS rows (blocks L1)

| Value | Rows |
|---|---|
| *null* | 13,273 |
| `'timsTOF fleX'` | 172 |

Only the Rabin dataset records an instrument at all, and it is free text rather
than an `MS:1000031` descendant. L1 requires a resolvable CV term for every row,
so **L1 is currently unreachable for 26 of 29 datasets** — not because the binding
is wrong, but because the value is absent.

The instrument is usually recoverable from the source publication or the original
file headers, so this is backfillable. It is a good first community task
(`CONTRIBUTING.md` §1).

Enum-valued columns are otherwise in decent shape and could be closed today:
`extraction_strategy` ∈ {`mzxml_profile`, `mzml_profile`, `txt_profile`} —
note `consolidated_csv` is declared by the exporter but never used;
`source_type` ∈ {`external`, `internal`};
`is_centroided` is `True` only for Rabin's 172 rows.

## Finding 3a — `shelfmark` values are mojibake

The Rabin / Crafting Documents dataset stores archival shelfmarks as `Pi�ce`
where `Pièce` is meant — a UTF-8/Latin-1 round-trip fault upstream in the CSV
read, affecting 155 distinct values.

Minor next to the other findings, but worth fixing **before** that column is ever
populated in a published table: a corrupted shelfmark is a corrupted citation to a
physical object, and mojibake tends to become permanent once it is downstream of a
join. The fix belongs in the reader, not in the stored values.

## Finding 3 — no file-level metadata anywhere

Every file's Parquet key-value metadata contains **only the pandas schema block**.
There is no:

- specification version
- CV reference or vocabulary version
- builder name and version
- build timestamp
- source-file checksum

So it is impossible to tell, from a file alone, which script wrote it or against
which schema. Given Finding 1 — where two exporters diverged silently — this is
precisely the gap that let the divergence go unnoticed.

**Recommended:** the writer stamps a `zoomzpeak` KV block into every file. Cheap,
additive, breaks no reader, and makes the validator able to report *why* a file is
non-conforming rather than just *that* it is.

## Finding 4 — compression is inconsistent

ZooMS spectra use **SNAPPY**; LC-MS MS2 and envelope files use **ZSTD**. Both are
valid; the inconsistency is the problem, since it is unintentional rather than
reasoned. ZSTD is the better default here (materially smaller on peak arrays, and
what mzPeak itself favours). Worth fixing on the next rebuild and stating in the
spec.

## Finding 5 — the LC-MS/MS side is clean

Sampled 251 of 6,002 MS2 files and 253 of 6,062 envelope files: **one schema each,
no errors.** Both reach L0 as they stand. The MS2 and envelope builders are in
better shape than the ZooMS ones and should be the model when they are merged.

(File counts have grown well beyond the 2,351 / 3,780 recorded in
`parquet_master/WALKTHROUGH.md` — worth updating there.)

---

## Finding 6 — the L2 context already exists, but is stranded

**This is the good news, and it changes the plan.**

`catalogs/drive_d_spectrum_inventory.parquet` carries **65 columns**, and roughly
forty of them are exactly the archaeological context that `PLAN.md` §4.3 defines
as L2 and that the spectra sidecars record as `null`. It was written by a
different pipeline and never joined back to the spectra tables.

Grouped by what they would bind to:

| Group | Columns |
|---|---|
| **Publication** | `article_file`, `publication_doi`, `publication_year`, `first_author`, `study_short` |
| **Taxon** | `taxon`, `taxon_confidence`, `common_group`, `species` |
| **Specimen** | `specimen_id`, `specimen_number`, `analytical_number`, `n_specimens`, `element`, `tissue`, `tissue_clean`, `endogenous` |
| **Place** | `site`, `country`, `latitude`, `longitude`, `altitude_m`, `deposition_type`, `excavation_year` |
| **Curation** | `museum`, `museum_location`, `museum_number` |
| **Chronology** | `age_c14_bp`, `age_c14_cal_bp`, `age_absolute_yr`, `age_value`, `age_unit`, `age_min`, `age_max`, `age_basis`, `age_category` |
| **Thermal history** | `mean_annual_temp_c`, `lapse_rate_corrected_temp_c`, `thermal_age_10c_ka`, `thermal_accel_ratio` — see §Thermal age below |
| **Laboratory** | `lab`, `extraction_protocol`, `digestion_method`, `digestion_clean`, `alkylation_agent`, `alkylation_clean`, `extraction_confidence` |
| **Instrument** | `instrument`, `instrument_make`, `instrument_make_pub`, `instrument_clean`, `acquisition_mode`, `acquisition_clean`, `fragmentation_method`, `dissociation_clean`, `has_timstof_mobility` |
| **Provenance of the metadata itself** | `meta_source`, `extracted_by`, `extracted_utc` |

Three observations:

1. **`meta_source`, `extracted_by`, `extracted_utc` already implement the
   provenance rule** the specification was going to introduce. The habit exists;
   it just needs generalising and making normative.
2. **The `_clean` / `_pub` column pairs are an un-named CV binding.** `instrument`
   vs `instrument_clean`, `digestion_method` vs `digestion_clean` — a raw
   as-reported value alongside a normalised one is exactly the shape of a CV
   binding, done by hand without a vocabulary behind it. Replacing `*_clean` with
   a resolved `*_cv_id` is a small change with a large payoff, and it means the
   L1/L2 work is *normalising* existing effort rather than starting from nothing.
3. **Everything is typed `string`** — including `latitude`, `longitude`,
   `altitude_m`, every `age_*` field, and all four thermal columns. Numeric fields
   held as text silently sort lexicographically and fail comparisons
   (`"9"` > `"10"`). This needs typing before it can be trusted, and typing it will
   surface parse failures that are currently invisible.

**Consequence for `PLAN.md`:** step 10 assumed L2 backfill was scholarly work
starting from zero. For the datasets covered by this inventory it is mostly a
*join plus a typing pass*. That is a much cheaper path to L2 and should be
attempted before asking the community to fill fields in by hand.

---

## Thermal age

Four columns, all currently `string`:

| Column | What it is |
|---|---|
| `mean_annual_temp_c` | Mean annual air temperature at the site (°C) |
| `lapse_rate_corrected_temp_c` | The above, corrected for altitude via lapse rate |
| `thermal_age_10c_ka` | Thermal age in ka, normalised to a 10 °C reference |
| `thermal_accel_ratio` | Acceleration ratio relative to that reference |

They depend on the chronology block (`age_*`) and the geography block
(`latitude`, `longitude`, `altitude_m`) to be computed at all, so those are inputs
rather than neighbours.

### Why thermal age belongs in its own repository

Agreed, and worth stating the reason in the specification, because it is the same
principle as the `rt` decision:

**Thermal age is not a measurement. It is a model output.** Every other column
audited here records something observed — an m/z value, an instrument, a museum
number, a radiocarbon date. Thermal age is *derived*, and derived through choices:
which temperature reconstruction, which lapse rate, which reference temperature,
which kinetic assumption, which burial-depth correction. Two labs can hold the
same specimen and honestly disagree.

Putting a model output in a measurement format would break the rule the rest of
the specification rests on. It would also date badly: the value changes when the
model improves, while the spectrum does not.

**How ZoomzPeak should handle it:**

- ZoomzPeak defines the **inputs** — chronology, geography, deposition context —
  with CV bindings and units, so a thermal-age model has something well-typed to
  consume. This is genuinely useful work and belongs here.
- ZoomzPeak defines a **binding point** for the result: a thermal-age value may be
  attached, but only carrying its model identity and version, never as a bare
  number. The LADO `SYE*` pattern (`PLAN.md` §5.4) already fits — a thermal age is
  an assignment produced by an analysis, not an intrinsic property of the bone.
- The model, its parameters, and its provenance live in the separate repository.

That split keeps the measurement format stable while the model is free to evolve,
and it makes any thermal age in the data traceable to the version that produced it
— which the current bare `thermal_age_10c_ka` string is not.

The existing four columns should therefore be treated as **inputs to migrate, not
a schema to adopt**: valuable data, in the wrong shape, in the wrong repository.

---

## Recommended order

Before publication (correctness, not polish):

1. **Finding 1** — relocate the two misfiled files out of the ZooMS spectra tree.
   This is a live footgun for anyone globbing the tree.
2. **Finding 3** — add the KV metadata block to the writers.

Soon after:

3. **Finding 4** — standardise on ZSTD at the next rebuild.
4. **Finding 6** — join and type the inventory. This is the cheapest large win
   available and unlocks L2 for a substantial fraction of the estate.
5. **Finding 1 (Rabin)** — promote `shelfmark` / `collection_name` / `provenance`
   into the shared schema rather than dropping them.

Then:

6. **Finding 2** — backfill `instrument` per dataset from the publications. The
   natural first community contribution.
