---
type: decision
status: active
tags: [adr, public-release, disclosure-review, licensing, provenance, zoomzpeak]
relatedTo: [zoomzpeak, ms1-data, ms2-data, parquet-master]
---

# ADR 0001 — Pre-publication disclosure review
**Date & Time:** 2026-09-08 (+02:00)

**Status:** Accepted — review passed with two remediations applied before the
first public push.

## Context

ZoomzPeak was published from the first commit rather than developed privately
and opened later (`PLAN.md` §9). Its content is copied from, or written about,
`MS1-Data`, `MS2-Data` and `parquet_master` — none of which is public, and all
of which contain unpublished research data.

Git history is not retractable in any practical sense. A secret pushed once is a
secret that must be rotated; unpublished collaborator data pushed once is a
conversation that cannot be un-had. `PLAN.md` §8.1 therefore made a disclosure
review a **blocking gate** on the first push rather than a tidy-up afterwards.

This ADR records that the review happened, what it checked, and what it changed.

## Decision

The review was run against the full tracked contents of the repository
immediately before the first push. **Publication was approved after two
remediations.**

## What was checked, and what was found

| # | Check | Result |
|---|---|---|
| 1 | Credentials, API keys, tokens | **Pass.** No matches outside the documentation that discusses handling them. |
| 2 | Unpublished data in files or fixtures | **Pass after remediation** — see below. |
| 3 | Absolute paths naming a person, institution or private project | **Pass.** No drive letters or home paths outside the local-working-copy line in `PLAN.md`. |
| 4 | Embargoed dataset identifiers | **Fail → remediated** — see below. |
| 5 | Sample-metadata sidecars | **Pass.** None committed. |

Additional checks not in the original §8.1 list:

| | Check | Result |
|---|---|---|
| 6 | ProteomeXchange accessions (`PXD…`, `MSV…`) | **Pass.** None present. |
| 7 | Fixture contents verified at the value level, not by inspection of the generator | **Pass.** Sample identifiers `EXAMPLE_001`–`006`; collections `Collection A/B/C`; `shelfmark` null in every row; `raw_path` under `example/`. |

## Remediations applied

### R1 — The example fixture is synthetic, not an excerpt

The obvious way to illustrate a well-annotated ZooMS table was to cut a few rows
from the richest real dataset. That dataset is a corpus of medieval relic labels
carrying live archival shelfmarks. A shelfmark identifies a specific extant
document, and a shelfmark next to a species assignment discloses an unpublished
finding about a named object.

The fixture is therefore **generated**: published COL1 marker masses plus
synthetic noise, fictional identifiers, `shelfmark` present in the schema but
null in every row. It declares itself synthetic in its own file metadata, so it
cannot be mistaken for real data when read out of context.

See `tests/fixtures/README.md`.

### R2 — The unpublished dataset is anonymised

The conformance audit originally named one dataset seven times, alongside its
row count, its schema divergence, and the observation that it is the only
dataset in the estate with resolved archaeological context. That is more
disclosure about work in progress than an engineering audit requires.

It is now **Dataset A** throughout, with a note at the head of the audit
explaining that the anonymisation is deliberate. No finding depended on the
name.

## Accepted residual risk

Recorded rather than resolved, because the trade was made knowingly:

1. **The fixture documentation credits the Crafting Documents project** — its
   funders, its investigators and the nature of its corpus — at the request of
   the project lead, and that information is publicly announced. The audit
   separately notes that "Dataset A" is the only dataset with archaeological
   context columns. An attentive reader could join those two facts. What is
   protected is the specifics: row counts, schema divergence, instrument
   coverage, and every measured value. This was judged an acceptable trade for
   giving the project proper credit.
2. **`PLAN.md` describes the contents of two private repositories** — script
   names, line counts, directory sizes. Judged unproblematic: they are
   repositories of the same organisation, and the descriptions are structural,
   not substantive.

## Consequences

- Publication proceeded. The repository is public as of this date.
- **The two remediations must not be silently reversed.** Anyone restoring a
  real excerpt to `tests/fixtures/`, or de-anonymising Dataset A, is undoing a
  disclosure decision and needs a corresponding ADR.
- **This review must be re-run before any further bulk copy** out of a private
  repository — in particular `PLAN.md` step 3, which migrates ten builder
  scripts. This ADR covers the scaffold, the plan, the audit and the fixture;
  it does not pre-approve the code migration.
- `CONTRIBUTING.md` carries the same rules in contributor-facing form: never
  commit data, never commit secrets, respect embargoes.

## A note on method

One finding in the original audit — that archival shelfmarks were mojibake —
was a **false positive**, caused by reading the data through a terminal that
could not render the characters. Verified at codepoint level, the values were
correct.

The lesson generalises to any future review, and to the validator: **never
diagnose an encoding or content fault from rendered output.** Assert on
codepoints or raw bytes. A display layer both invents faults that are not there
and hides ones that are. The same discipline applies to disclosure review —
checks 6 and 7 above were run against actual values, not against the code that
was believed to produce them.

## Related

- `PLAN.md` §8.1 — the gate this ADR discharges
- `docs/conformance_audit_2026-09-08.md` — Finding 3a, the withdrawn finding
- `tests/fixtures/README.md` — what the fixture withholds, and why
- `CONTRIBUTING.md` — the contributor-facing form of these rules
