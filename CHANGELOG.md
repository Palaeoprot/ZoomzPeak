# Changelog

All notable changes to ZoomzPeak are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/), applied to the
**specification** as well as the code: any change that would break an existing
reader requires a version bump and a migration note.

## [Unreleased]

Pre-release. The specification is not yet stable and nothing here should be
depended on.

### Added
- `PLAN.md` — full design and migration plan: survey of the existing builders,
  the `mzPeakMS-ZooMS` profile, the ontology binding layer, and the migration
  sequence.
- Repository scaffold: README, Apache-2.0 code licence, CC-BY-4.0 specification
  licence, Code of Conduct, contributing guide, citation metadata.
- Logo (option 2, "Collagen Fragment") as `docs/assets/mark.png`.

### Decided
- Project name is **ZoomzPeak**, following the wordmark. The GitHub repository is
  renamed from `ZooMzPeak` to match.
- Scope covers **both** the ZooMS (MALDI-ToF MS1) and the LC-MS/MS (MS2 + MS1
  precursor envelope) builders, as one specification family.
- The repository is **public from the first commit**, pre-release until v0.1.
- The archaeological binding layer anchors on **LADO** (LEIZA), which is published
  and dereferenceable today, rather than on ARCH-ON, which has no released
  namespace yet.

### Known gaps
- No vocabulary bindings exist for the ZooMS schema yet — this is the central gap
  the project sets out to close.
- No builders have been migrated into this repository yet; they still live in the
  private `MS1-Data` and `MS2-Data` repositories.
