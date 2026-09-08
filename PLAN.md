---
type: plan
status: draft
tags: [zoomzpeak, mzpeak, arch-on, lado, archaeology-link, nfdi4objects, zooms, parquet, ontology, psi-ms, cidoc-crm, palaeoproteomics]
relatedTo: [parquet-master, ms1-data, ms2-data, reference-data, pyzooms]
---

# ZoomzPeak — Migration & Design Plan
**Date & Time:** 2026-09-08 (+02:00)

A plan for extracting the parquet-building work out of `MS1-Data` / `MS2-Data` /
`Reference-Data` into a single public repository, and for giving the ZooMS parquet
format a proper, ontology-anchored specification (`mzPeakMS-ZooMS`).

Target remote: <https://github.com/Palaeoprot/ZoomzPeak> (rename pending, see §0)
Local working copy: `C:\Users\matth\Documents\GitHub\ZoomzPeak`
Community discussion: [Matrix room](https://matrix.to/#/!QpobrZgJZFYpmEnoKa:matrix.org?via=matrix.org&via=archaeo.social)

---

## 0. Naming — settled

The repository was originally announced as `Palaeoprot/ZooMzPeak` (capital M,
reading as "ZooMS" + "mzPeak"), while the local folder was `ZoomzPeak`.

**DECIDED (2026-09-08): the project is `ZoomzPeak`.** The logo wordmarks (§10) are
all set that way, with the lowercase `z` as the pivot between "Zoomz" and "Peak";
resetting them to put a capital M mid-word would break the wordmark's rhythm. The
artwork was further along than the URL, so the URL moves.

**Consequence — a GitHub-side rename is required.** The remote was announced as
`Palaeoprot/ZooMzPeak`; it must be renamed to `Palaeoprot/ZoomzPeak`. GitHub
redirects the old path automatically, so nothing already circulated breaks. The
local folder is already correctly named. This is the one step in §6.1 that cannot
be done from here — see the note there.

---

## 1. What exists today (survey findings)

### 1.1 The builder code — currently scattered across three repos

| Location | Size | Role |
|---|---|---|
| `MS1-Data/scripts/10_Export_MZPeak_Parquet.py` | 155 ln | Bespoke exporter, one dataset (Collins 2026 Rabin); joins peaklist CSV × plate metadata × run YAML |
| `MS1-Data/scripts/11_Export_MZPeak_Parquet_All.py` | 300 ln | Generalized exporter, 4 source strategies (`consolidated_csv` → `txt_profile` → `mzxml_profile` → `mzml_profile`); defines the canonical 13-column `SCHEMA` |
| `MS1-Data/scripts/13_Pick_Peaks_ZooMS.py` | 132 ln | Peak-picks `is_centroided=False` rows via `pyZooMS.peakPickerSciPy`; writes to `…/picked/` |
| `MS2-Data/spectrum_extraction/universal_parquet_ingest.py` | — | Dual-output MS2 table + MS1 envelope in one pass, consistent `spec_idx` |
| `MS2-Data/spectrum_extraction/extract_ms1_envelope_*.py` | 3 files | Envelope-only extractors (parallel / standalone / mzML) |
| `MS2-Data/spectrum_extraction/generate_sdrf.py` | — | SDRF-Proteomics sidecar TSV per PXD |
| `MS2-Data/spectrum_extraction/audit_raw_completeness.py` | — | Two-phase-commit safe-to-delete gate |
| `MS2-Data/spectrum_extraction/update_zooms_manifest.py` | — | Filesystem crawler → master manifest parquet |
| `Reference-Data/MANIFESTS/paths.py` | — | Portable path resolution, imported by all of the above |
| `Reference-Data/MANIFESTS/ms1_envelope_schema.cv.yaml` | — | **The only existing ontology binding** — PSI-MS CV mapping for the MS1 envelope schema |

Two documents already do real conceptual groundwork and must come along:
`MS2-Data/COMPARATIVE_REPORT_MZPEAK_VS_INTERNAL_PARQUET.md` and
`MS2-Data/MS2-Data Documentation/mzPeak_ Designing a Scalable, Interoperable…md`.

### 1.2 The data — stays where it is

`parquet_master/ZooMS_parquet` is **55 GB**; `MS1-Data` is 120 GB and `MS2-Data`
41 GB. None of that moves. ZoomzPeak is a **code + specification** repo that
*writes into* `parquet_master`, exactly as the current scripts do via `paths.py`.

Current ZooMS holdings: 29 datasets under
`ZooMS_parquet/zooms_ms1_maldi/dataset_id=<name>/spectra.parquet`, a parallel
`picked/` tree, an `insilico_libraries/` tree (per-species per-gene COL parquets),
and 29 `experiments_metadata/<dataset_id>.json` sidecars.

### 1.3 The honest gap

The exporters' docstrings say *"following mzPeak-style conventions
(https://www.mzpeak.org/)"*, but nothing in the ZooMS pipeline is actually bound to
a controlled vocabulary:

- **No CV mapping for the ZooMS schema at all.** `ms1_envelope_schema.cv.yaml`
  covers only the LC-MS/MS envelope table. The 13 ZooMS columns (`file_id`,
  `dataset_id`, `source_type`, `raw_path`, `sample_id`, `scan_number`, `rt`,
  `instrument`, `mz`, `intensity`, `n_peaks`, `is_centroided`,
  `extraction_strategy`) have no term bindings.
- **`instrument` is a free-text string** (`"timsTOF fleX"`), not an `MS:1000031`
  instrument-model child term.
- **No mzPeak container.** We write bare Hive-partitioned parquet directories;
  mzPeak v0.9 specifies a ZIP of `*_data.parquet` tables plus an
  `mzpeak_index.json` manifest. We have neither the index nor the metadata tables.
- **The archaeological half is entirely unbound.** The sidecar JSONs carry
  `species`, `citation`, `sample_provenance` — all `null`, all free-text-when-filled,
  none tied to a taxonomy, a place gazetteer, a period vocabulary, or an
  artefact/material typology. This is precisely the arch-on layer.
- The sidecars honestly flag this themselves (`_enrichment_note`), which is good
  practice worth preserving as a normative rule.

### 1.4 arch-on: current status, and what that means for us

I checked <https://seco.cs.aalto.fi/projects/arch-on/>. ARCH-ON is a
University of Helsinki / KU Leuven / Aalto (SeCo) project on ontology-based
archaeological knowledge representation, with a DHNB 2026 paper. **It does not yet
publish a dereferenceable namespace, OWL file, SPARQL endpoint, or licence** — the
project page lists prior work (FindSampo, CoinSampo, PASampo, ARIADNEplus) but no
technical release.

So we cannot hard-code arch-on IRIs today. The plan below therefore uses an
**indirection layer**: every archaeological field is bound to a term *record*
(`prefix`, `id`, `label`, `source`, `status`) rather than to a bare IRI string, so
that swapping in real arch-on IRIs later is a data edit in one YAML file, not a
schema migration. Until then we bind to the vocabularies arch-on itself builds on
and that *are* dereferenceable today — CIDOC-CRM, ARIADNEplus, NCBI Taxon, Getty
AAT, PeriodO — and mark each binding `status: provisional`.

**Action:** raise this in the Matrix room and, in parallel, contact the SeCo /
ARCH-ON team asking for the intended namespace and release timeline. Their answer
determines whether §5's `arch:` prefix resolves in v1.0 or stays provisional.

---

## 2. Scope of the repository

**In scope**
1. All ZooMS (MALDI-ToF MS1) parquet builders, peak pickers, and validators.
2. The LC-MS/MS MS2 + MS1-envelope parquet builders — same format family, same
   CV-binding machinery; splitting them would fork the spec.
3. The `mzPeakMS-ZooMS` specification: schema, CV bindings, conformance levels,
   validator.
4. `paths.py` (re-homed) and the sidecar-metadata contract.
5. Small synthetic/public test fixtures only.

**Out of scope**
- Any real spectra. No parquet data files, no `.raw`, no `.mzML`, no `collagens/`.
- Downloaders (`universal_ingest.py`, `download_zenodo_datasets.py`) — these are
  acquisition, not format. They stay put and simply import the ZoomzPeak writer.
- Search-engine / PSM territory (pSAGEd, PhASTM) — downstream consumers.

---

## 3. Proposed repository layout

```
ZoomzPeak/
├── README.md                     ← what it is, who it's for, links (mzPeak, arch-on, Matrix)
├── LICENSE                       ← code licence (see §8)
├── LICENSE-SPEC                  ← CC-BY-4.0 for spec + vocabulary files
├── CITATION.cff
├── CONTRIBUTING.md               ← incl. how to propose a new CV binding
├── CODE_OF_CONDUCT.md
├── CHANGELOG.md
│
├── spec/
│   ├── mzPeakMS-ZooMS-v0.1.md    ← the human-readable specification
│   ├── conformance.md            ← Level 0 / 1 / 2 (see §4.3)
│   └── rationale.md              ← from COMPARATIVE_REPORT_MZPEAK_VS_INTERNAL_PARQUET.md
│
├── vocab/                        ← THE ontology binding layer (§5)
│   ├── zooms_spectra.cv.yaml     ← NEW: PSI-MS bindings for the 13 ZooMS columns
│   ├── ms1_envelope.cv.yaml      ← moved from Reference-Data/MANIFESTS
│   ├── ms2_spectra.cv.yaml       ← NEW
│   ├── psm_results.cv.yaml       ← NEW
│   ├── archaeo_context.cv.yaml   ← NEW: LADO / CIDOC-CRM archaeological context (§5.4)
│   ├── prefixes.yaml             ← prefix → base-IRI table, single source of truth
│   └── README.md                 ← how to read a binding record; provisional vs stable
│
├── src/zoomzpeak/                ← installable package (`pip install -e .`)
│   ├── paths.py
│   ├── schema.py                 ← pyarrow schemas, generated FROM vocab/*.yaml
│   ├── writers/{zooms,ms2,envelope}.py
│   ├── readers/                  ← duckdb/polars convenience loaders
│   ├── peakpick.py               ← from 13_Pick_Peaks_ZooMS.py
│   ├── sidecar.py                ← experiments_metadata JSON contract + validator
│   ├── cv.py                     ← term lookup, OLS resolution, cache
│   ├── mzpeak_export.py          ← §4.2 bridge to a real .mzpeak container
│   └── validate.py               ← the conformance checker
│
├── cli/                          ← `zoomzpeak build|pick|validate|export|describe`
├── tests/  +  fixtures/          ← tiny synthetic spectra, public-domain only
├── docs/                         ← rendered spec, column reference, examples
├── examples/                     ← notebooks: query with DuckDB, round-trip to mzPeak
└── .github/workflows/ci.yml      ← lint + tests + `validate` over fixtures
```

---

## 4. The `mzPeakMS-ZooMS` profile

### 4.1 Why a profile rather than plain mzPeak

mzPeak v0.9 assumes a chromatographic run: a scan hierarchy, retention time, an
interleaved MS1…MSn stream. MALDI-ToF ZooMS has **one spectrum per sample and no
time axis** — the existing `rt` column is, as `WALKTHROUGH.md` already records, an
artifact of the source file format, not an elution time. Rather than fabricate
synthetic LC metadata, we declare a documented **profile**: a constrained,
CV-anchored specialisation of mzPeak for single-shot MALDI, using mzPeak's own
entity-type / data-kind extension mechanism — the same mechanism it uses for MS
imaging, which is architecturally the closest existing case (per-pixel rather than
per-elution-time).

### 4.2 Two representations, one schema

- **Analysis form (primary, what we already have):** Hive-partitioned parquet
  directories under `parquet_master`, queried directly by DuckDB/Polars/pyZooMS.
  Fast, no unpacking. This is what the pipeline reads and writes.
- **Interchange form (new):** `mzpeak_export.py` packs one dataset into a
  conformant `.mzpeak` ZIP — `*_data.parquet` + metadata tables +
  `mzpeak_index.json` — for deposition, PRIDE/Zenodo upload, and third-party tools.

Both are generated from the *same* `vocab/` bindings, so they cannot drift.
A round-trip test (analysis → interchange → analysis, assert equality) is a CI gate.

### 4.3 Conformance levels

| Level | Requirement |
|---|---|
| **L0 — Structural** | Column names, arrow types, and partition layout match the schema. |
| **L1 — CV-bound** | Every column resolves to a term in `vocab/`; `instrument` is a valid `MS:1000031` descendant, not free text. |
| **L2 — Contextualised** | Sidecar carries resolved archaeological context: taxon, material, site/place, period, and a citation DOI — each with a `source` provenance tag. |

`zoomzpeak validate` reports the highest level a dataset reaches and names the exact
fields blocking the next one. Today's 29 datasets would all land at L0.

### 4.4 Schema changes required to reach L1/L2

Additive only — existing readers keep working:

| Column | Change |
|---|---|
| `instrument` | keep free text, **add** `instrument_cv_id` (e.g. `MS:1003005`) + `instrument_cv_label` |
| `is_centroided` | bind to `MS:1000127` centroid / `MS:1000128` profile spectrum |
| `mz` / `intensity` | bind to `MS:1000514` / `MS:1000515` (already the mzPeak arrays) |
| `rt` | **document as non-physical**; bind to a local `zooms:` term, explicitly *not* `MS:1000894`. This is a correctness fix — the current implicit reading is wrong. |
| `extraction_strategy` | promote to a closed enum, defined in `vocab/` |
| `source_type` | closed enum (`internal` / `external` / `zenodo` / `pride`) |
| *(new)* `matrix_cv_id` | MALDI matrix (CHCA etc.), PSI-MS matrix-solution family |
| *(new)* `digestion_cv_id` | enzyme, PSI-MS `MS:1001045` family |
| *(new)* `spectrum_id` | stable, content-addressed spectrum identifier for citation |

### 4.5 Sidecar contract

`experiments_metadata/<dataset_id>.json` becomes a schema-validated document
(JSON Schema in `spec/`), keeping the existing and genuinely good
`_metadata_source` / `_enrichment_note` provenance habit: **every field carries how
it was established, and an unconfirmed field stays blank rather than guessed.**
That rule becomes normative in the spec, not merely a convention.

---

## 5. Ontology binding — the arch-on layer

### 5.1 Binding record format

Every field in `vocab/*.cv.yaml` is a record, not a bare string:

```yaml
site_name:
  prefix: crm
  id: E53_Place
  label: Place
  source: CIDOC-CRM 7.1.3
  status: provisional          # provisional | stable | local
  arch_on_candidate: true      # revisit when ARCH-ON publishes
  note: >
    Placeholder pending an ARCH-ON findspot class. Values are free text today;
    target is a gazetteer IRI (Pleiades / PeriodO-linked / national registers).
```

`vocab/prefixes.yaml` is the single place a prefix maps to a base IRI. When
ARCH-ON publishes, we add `arch:` there and flip records from `crm:` → `arch:` with
`status: stable`. **No code changes, no schema migration.**

### 5.2 Which vocabulary covers what

| Domain | Vocabulary | Status today |
|---|---|---|
| Instrument, acquisition, spectrum arrays, enzymes, matrix | **PSI-MS** (`MS:`) | stable, dereferenceable via OLS |
| Sample-level experimental metadata | **SDRF-Proteomics** (`generate_sdrf.py` already emits it) | stable |
| Species / taxon | **NCBI Taxon** (`NCBITaxon:`) | stable |
| Anatomical element (bone, tooth, skin) | **UBERON**; Getty **AAT** for worked materials (parchment, leather) | stable |
| Site, findspot, place | **LADO** `arno:DiscoverySite` / `crm:E53_Place` + gazetteer IRI (Pleiades) | **stable** (§5.4) |
| Chronological period | **PeriodO** | stable vocabulary, provisional binding |
| Artefact / object typology | **Getty AAT**, ARIADNEplus AO-Cat | provisional → arch-on |
| Archaeological event / context | **LADO** `SYE*` observation pattern over `crm:E5_Event` | **stable** (§5.4) |
| Analytical observation → species call | **LADO** `SYE5_Observation` / `SYE3_Assignment` | **stable** (§5.4) |
| Geometry / coordinates | **GeoSPARQL** (`asWKT`, `asGeoJSON`) via LADO | stable |
| Dataset provenance | **DCAT** + **PROV-O** | stable |

CIDOC-CRM is the right backbone because ARCH-ON's own stated lineage (FindSampo,
CoinSampo, PASampo, ARIADNEplus) sits on exactly that stack — so a later migration
is a refinement, not a rewrite. But we do not have to bind to bare CRM: LADO
(§5.4) is an already-published CRM profile that does much of this work for us.

### 5.4 archaeology.link / LADO — available now, unlike ARCH-ON

<https://archaeology.link/> is the LEIZA (Leibniz-Zentrum für Archäologie) data
hub, run within **NFDI4Objects**. Unlike ARCH-ON (§1.4), it has shipped:

| Resource | What it is | Usable? |
|---|---|---|
| **LADO** — Linked Archaeological Data Ontology | v1.1, 2025-05-20, Thiery & Mees (LEIZA). Namespace `http://archaeology.link/ontology#`, prefix `lado:`. CC-BY-4.0, [DOI 10.5281/zenodo.15477358](https://doi.org/10.5281/zenodo.15477358), source at [archaeolink/lado](https://github.com/archaeolink/lado) (`lado.ttl`, 1,949 lines), Widoco docs at <https://archaeolink.github.io/lado/> | **Yes — adopt** |
| Linked Open Samian Ware / ARS | Exemplar datasets modelled in LADO | Reference only |
| Linked Open Ships / NAVIS.one Maritime Thesaurus | Maritime vocabulary | Not applicable |
| Wikidata projects | Bidirectional links to Wikidata | Later, for taxon/site reconciliation |

**Why this changes the plan.** LADO gives us a *dereferenceable, DOI-cited,
CC-BY-4.0, actively maintained* archaeological anchor today, where §1.4 could only
offer provisional raw CIDOC-CRM. Several bindings in §5.2 move from
`status: provisional` straight to `status: stable`.

**What we take from it.** LADO imports and aligns to CIDOC-CRM, PROV-O, SKOS,
GeoSPARQL, FOAF and Pleiades — precisely the scaffolding §5.2 needed. The parts
that fit us directly:

- `arno:DiscoverySite`, `arno:Site`, `arno:Place`, `arno:SpatiotemporalInformation`
  and `pleiades:Place` for findspot — a far better fit than bare `crm:E53_Place`.
- The **`SYE*` observation/assignment pattern** — `SYE5_Observation`,
  `SYE7_QuantitativeAnalysis`, `SYE3_Assignment`, `SYE4_Indication`,
  `SYE10_Citation`. This maps almost one-to-one onto what a ZooMS result *is*:
  a spectrum (`SYE1_InformationCarrier`) bears peak markers (`SYE2_Feature`),
  a quantitative analysis yields an indication, and an assignment records the
  species call with its citation. This is the single most valuable find here —
  it means the ZooMS species-ID chain can be expressed in a published archaeological
  ontology rather than in a local vocabulary we invent.
- GeoSPARQL geometry and the PROV-O provenance vocabulary, which also serve §4.5's
  "every field records how it was established" rule.

**What we must not take.** The bulk of LADO's `ontology:` namespace is
samian-ware-specific — `ChiefPotter`, `MouldMaker`, `Die`, `DieImpression`,
`Potform`, `KilnRegion`, `gentilicium`, `pottername`. These are LEIZA's ceramics
domain and have no ZooMS meaning. Adopting them by analogy would be exactly the
kind of forced mapping §4.1 refuses for `rt`. Take the scaffolding and the `SYE*`
pattern; leave the pottery.

**Two mechanical notes for `prefixes.yaml`:**

1. The namespace is `http://archaeology.link/ontology#` — **`http`, not `https`**,
   even though the website and docs are HTTPS. An IRI is an identifier, not a
   fetch target; silently "upgrading" it to `https://` creates a different,
   non-matching identifier. Record it verbatim.
2. LADO uses `:` , `lado:` and `ontology:` as three prefixes for the *same*
   namespace. Pick `lado:` as our canonical form and normalise on read.

### 5.5 NFDI4Objects — the route in

Checked 2026-09-08. archaeology.link sits inside **NFDI4Objects**, the German
national research-data consortium for material culture and object sciences (70+
institutions). Three things make this a better first approach than SeCo:

1. **Biomolecular archaeology is explicitly in their remit.** Their stated
   disciplines include Genetics, Archaeometry, (Palaeo-)Anthropology and Zoology
   alongside the archaeologies. A ZooMS data standard is not an awkward fit; it is
   the sort of thing the consortium exists to support.
2. **They already run the infrastructure we would otherwise have to build** —
   SPARQL endpoints, FAIRification tooling (Alligator, Academic Meta Tool,
   re3dragon), and an established route for external projects to publish
   vocabularies and Linked Open datasets. archaeology.link is positioned under
   Task Areas 2 and 4.
3. **Named, reachable maintainers.** Florian Thiery and Allard W. Mees (LEIZA,
   "Scientific IT, Digital Platforms and Tools") are the responsible persons for
   both archaeology.link and LADO. General contact: `info@nfdi4objects.net`.

**Why we open here rather than with SeCo:** with LADO we can arrive with a concrete
proposal against something that already exists — "here is a ZooMS profile, here is
how the `SYE*` observation pattern maps onto a species assignment, does this look
right to you?" With ARCH-ON there is nothing published to build against yet, so any
approach is necessarily an expression of interest. Do both, but lead with LEIZA.

There is a pleasing symmetry worth using in the approach: this project would end up
bridging **HUPO-PSI** (the measurement half, §10.4) and **NFDI4Objects/LEIZA** (the
archaeological half). Neither community currently has a standard that spans both,
and that gap is exactly what a ZooMS dataset falls into.

### 5.3 Resolution and caching

`cv.py` resolves terms against **EMBL-EBI OLS** and caches to `vocab/.cache/`, so
validation works offline and CI is not network-flaky. A scheduled CI job re-resolves
and opens a PR when an upstream term is obsoleted or relabelled.

---

## 6. Migration steps

Ordered, each independently reviewable. Nothing is deleted from the source repos
until step 8.

1. **Rename** `ZoomzPeak` → `ZoomzPeak`; `git init`; add remote; push an empty
   `main` with README + LICENSE + CODE_OF_CONDUCT so the repo is publicly legible
   from day one.
2. **Pre-publication review (§8.1)** of the ten code files from §1.1, *before* any
   of them is committed. This is the gate the public-from-day-one decision creates.
3. **Copy** (not move) those files into `src/zoomzpeak/`, refactored from top-level
   scripts into importable modules with a thin CLI. Behaviour stays byte-identical
   at this step — no schema changes yet. The LC-MS/MS builders come across in the
   same pass as the ZooMS ones.
4. **Golden-output test**: rebuild 2–3 existing datasets with the new package and
   assert the parquet is byte-identical to what is in `parquet_master` today.
   This is the safety net for everything after it.
5. **Move** `ms1_envelope_schema.cv.yaml` → `vocab/ms1_envelope.cv.yaml`; author
   the three new CV files (`zooms_spectra`, `ms2_spectra`, `psm_results`) and
   `archaeo_context.cv.yaml` (LADO-anchored, §5.4); add `prefixes.yaml`.
6. **Generate `schema.py` from `vocab/`** so the pyarrow schema and the CV binding
   are provably the same artifact.
7. **Write the spec** (`spec/mzPeakMS-ZooMS-v0.1.md`), folding the two existing
   MS2-Data documents in as `spec/rationale.md`.
8. **Implement `validate` and `mzpeak_export`**; run `validate` over all 29
   datasets and publish the report as `docs/conformance_status.md`.
9. **Additive schema bump** (§4.4) → rebuild the 29 datasets to L1 → then, and only
   then, replace the originals in `MS1-Data`/`MS2-Data` with a stub pointing at
   ZoomzPeak, and update `WALKTHROUGH.md`'s links.
10. **Backfill L2 context** dataset by dataset, from the source publications. This is
   scholarly work, not code, and is the natural first community contribution — one
   PR per dataset, discussed in the Matrix room.

---

## 7. What we are asking the community for

The README should state this plainly, because a public repo with an unclear ask
gets no contributors:

1. **Fill the L2 gap** — one PR per dataset adding taxon / site / period / citation.
2. **Review the CV bindings** — especially anywhere marked `provisional`.
3. **Tell us what breaks** — other ZooMS labs' peaklist formats that our four
   extraction strategies do not cover.
4. **ARCH-ON alignment** — the SeCo team's input on §5, once their namespace exists.

---

## 8. Licensing, citation, governance

- **Code:** Apache-2.0 (patent grant; matches the HUPO-PSI / Apache Parquet ecosystem).
- **Spec + `vocab/`:** CC-BY-4.0, so the bindings can be reused and cited.
- **CITATION.cff** from day one; mint a Zenodo DOI at v0.1.
- **Governance:** decisions in the Matrix room, recorded as ADRs in `docs/adr/`;
  breaking spec changes require a minor-version bump and a migration note.
### 8.1 Pre-publication check — a blocking gate, not a nicety

The repo is public from the first commit, so this must pass **before** step 2's copy
is committed. Git history is not retractable: a secret pushed once is a secret
rotated, and unpublished collaborator data pushed once is a conversation you cannot
un-have.

Every file copied out of `MS1-Data` / `MS2-Data` (both non-public) gets a
read-through against this list:

1. **No credentials or tokens.** PRIDE/MassIVE/Zenodo API keys, Google Drive
   tokens, anything that looks like a secret. Provision these interactively at
   runtime and read them from the environment — never a default in code, never a
   committed `.env`, never echoed into a log.
2. **No unpublished data**, including embedded sample tables, species assignments,
   or peak lists pasted into a docstring or test fixture. Fixtures must be
   synthetic or from a published, licence-compatible dataset.
3. **No absolute paths naming a collaborator, institution, or unpublished project.**
   `paths.py` is already environment-variable-driven, which covers most of this, but
   the copied scripts contain hardcoded dataset folder names — check each one is a
   published study.
4. **No embargoed dataset identifiers.** Several dataset IDs in `parquet_master`
   are 2026 studies; confirm each is out before its name appears in a public README,
   test, or CV file.
5. **Scrub the sample metadata sidecars** if any are committed as examples — they
   carry `sample_provenance` free text.

Record the outcome in `docs/adr/0001-public-release-review.md` so it is auditable,
and re-run the check for any later bulk copy from a private repo.

---

## 9. Decisions taken, and what is still open

### Decided (2026-09-08)

- **Scope — both sides.** The LC-MS/MS builders (MS2 spectra + MS1 precursor
  envelopes) come into ZoomzPeak alongside the ZooMS ones, as one spec family with
  one CV-binding mechanism. §2 and §3 already assume this.
- **Visibility — public from the first commit.** `main` is labelled pre-release
  until v0.1. See §8.1 for what this forces us to do *before* step 6.1.
- **Naming — `ZoomzPeak`.** Follows the artwork; the GitHub repo is renamed to
  match (§0).
- **HUPO-PSI engagement.** PSI have invited palaeoproteomics involvement; MC is
  taking the mark and the `rt`/profile question to them directly (§10.4).
- **Logo — option 2, "Collagen Fragment"** (peaks merging into a bone/tooth
  fragment). Options 1, 3 and 4 retired. See §10.2.

### Still open

1. **arch-on contact** — do you already have a line to the SeCo / ARCH-ON team, or
   should the Matrix room be the first approach? (§5.4 adds LEIZA / NFDI4Objects
   as a second, more concrete approach.)
2. **`insilico_libraries/`** — the per-species COL parquets are a different kind of
   object (theoretical, not observed). Own schema in this spec, or out of scope?
3. **Logo vector source** — option 2 is chosen; can you supply (or regenerate) it
   as SVG, and confirm the artwork's provenance for §10.4?

---

## 10. Visual identity

`mark.png` (1536×1024) is a **four-option exploration sheet**, not a finished mark:
four candidate logos with captions and a "RECOMMENDED" badge on option 1. Useful
input, but not yet something a repo can ship. What follows is an assessment and
what is needed to turn it into a usable asset.

### 10.1 The wordmark decides the naming question

All four are set as **`ZoomzPeak`** — see §0. Whichever way that goes, the wordmark
and the repository name must match before the first public commit; a repo whose
README logo spells the project differently from its URL looks unfinished.

### 10.2 The four options

| # | Concept | Assessment |
|---|---|---|
| **1. Spectrum Z** | Peaks rising into a `Z`, with a bone detail | The strongest *idea* — it carries mass spec and the Z in one form. But as drawn the bone/peak overlap is muddy: there is a visible smudge where the shapes intersect, and the notch reads as an artifact rather than an intentional bone contour. Needs redrawing as clean vector before it can be judged fairly. |
| **2. Collagen Fragment** | Peaks merging into a bone/tooth fragment | **CHOSEN (2026-09-08).** Conceptually the most honest: bone *is* the sample, and peaks→bone is literally what ZooMS does. Simple silhouette, distinct at small sizes, no fine internal detail to lose. Least likely to be mistaken for a generic analytics logo. |
| **3. Zoom Lens** | Circle/lens around a peak | The ring adds weight without adding meaning, and it crowds the peaks. "Zoom" is a pun on ZooMS, not a description of what the tool does — this option takes the pun literally. Weakest of the four. |
| **4. Taxonomic Peak** | Triangle with negative-space layers | The internal negative space is the whole idea and it is the first thing to disappear below ~32 px. The vertebrate reading is not legible even at full size. Would need heavy simplification. |

Ranked: **2 > 1 > 4 > 3**. **Option 2 is chosen.** Options 1, 3 and 4 are retired;
keep `mark.png` in `docs/assets/` as a record of the exploration, but only option 2
is developed further.

Because option 2 was chosen, §10.3's small-size worries are largely answered — the
bone silhouette is a solid mass with no internal negative space, so it survives
scaling better than 1 or 4 would have. The remaining risk is the four peak strokes
to its left: they thin toward the left edge and are the part that will fill in or
drop out at 16 px. Test those specifically, and be willing to reduce four peaks to
three at favicon scale.

### 10.3 What is missing before this ships

1. **Vector source.** A 1.2 MB raster comp sheet is not a logo. We need SVG for the
   chosen mark — a repo logo gets rendered at 16 px (favicon), 400 px (README),
   and print size for a paper figure.
2. **A monochrome variant.** Single-colour black and single-colour white, for
   printing, embossing, and any context that cannot carry blue.
3. **A dark-mode variant.** The comps are blue on white; GitHub READMEs render on
   dark backgrounds for many users. The mid-blue will need lightening.
4. **A favicon-scale test.** Both surviving options have thin peak strokes that may
   fill in at 16 px. Test before committing.
5. **The gradient goes.** There is a blue-to-blue gradient in these comps. It will
   not survive small sizes, monochrome, or fax-quality print. Flat colour.
6. **Files:** `docs/assets/logo.svg`, `logo-mono.svg`, `logo-dark.svg`, `favicon.ico`.

### 10.4 Two things to settle before the mark is public

**Derivation from mzPeak — being handled directly.** The mark is based on mzPeak's,
and mzPeak is a **HUPO-PSI** standard, so a visually derivative mark could otherwise
read as HUPO-PSI endorsement of a spec they had not reviewed.

**Update (2026-09-08):** HUPO-PSI have invited us to get involved on the
palaeoproteomics side, and MC is raising the mark with them directly. That converts
this from a risk to be managed into an opening — and it materially improves §4.1
too. A profile developed *with* PSI rather than alongside them can aim at being a
recognised mzPeak profile rather than a private dialect, which is a much stronger
position for the ZooMS community. Two things to get out of that conversation:

1. **Explicit sign-off on the mark** — a one-line "yes, family resemblance is
   fine" on the record, so the question never resurfaces.
2. **The `rt` question (§4.1) put to PSI directly.** Single-shot MALDI with no time
   axis is a genuine gap in a chromatography-shaped format, and PSI are the right
   people to say whether the entity-type / data-kind extension mechanism is the
   intended route or whether they would rather solve it in the core spec. Their
   answer changes §4 more than any other open question here.

§5.4's LEIZA/LADO approach is a separate conversation and can run in parallel.

**Provenance of the artwork.** If these comps were AI-generated, say so in
`docs/assets/README.md`. For a public, citable, CC-licensed community project the
origin of the visual identity should be on the record — and it affects what we can
assert about ownership in §8.

### 10.5 Licensing — the logo is not code

Add to §8: **the logo is excluded from both the Apache-2.0 and CC-BY-4.0 grants.**
Marks identify a project; a CC-BY logo can be reused by anyone including on work we
have no part in, which is precisely what a project identity must prevent. State in
`LICENSE`/`README`: *"The ZoomzPeak name and logo are not covered by the code or
specification licences. All rights reserved."* This is standard practice for
community specs and is not in tension with being an open project.
