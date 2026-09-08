# Contributing to ZoomzPeak

Thank you for considering it. This project is being built in the open precisely
because a data standard written by one lab is not a standard.

ZoomzPeak is a [**PAASTA**](https://paasta-community.github.io/) initiative --
Palaeoproteomics And Archaeology, Society for Techniques and Advances -- so it
inherits PAASTA's premise: an open, supportive place to ask questions and share
experience. Newcomers and early-career researchers are explicitly welcome, and
"I don't understand why it works this way" is a useful contribution, not a
nuisance.

Please read the [Code of Conduct](CODE_OF_CONDUCT.md) first, and
[`PLAN.md`](PLAN.md) for where the project is heading.

**Discussion happens in the [Matrix room](https://matrix.to/#/!QpobrZgJZFYpmEnoKa:matrix.org?via=matrix.org&via=archaeo.social).**
For anything larger than a typo, it is worth raising there or in an issue before
writing code — the design is still moving.

---

## The most useful things you can contribute

You do not need to write Python to help. In rough order of how much they would
help right now:

### 1. Archaeological context for datasets

The single biggest gap. Most datasets currently have spectra but no resolved
context — no taxon, site, period, or citation. Filling one dataset in is a
self-contained contribution: **one pull request per dataset.**

### 2. Review of vocabulary bindings

Every column and metadata field is bound to a controlled-vocabulary term in
`vocab/*.yaml`. Anything marked `status: provisional` is a guess we would like
checked by someone who knows that vocabulary properly. Telling us a binding is
wrong is a genuine contribution, even without a proposed replacement.

### 3. Formats that do not load

If your lab's ZooMS peaklist export is not readable, that is a bug. See below.

### 4. Code, tests, documentation

Normal open-source contributions, very welcome.

---

## Ground rules specific to this project

These come from hard experience and are not negotiable, because breaking them
produces data that looks fine and is quietly wrong.

### Never fabricate a value

If a field cannot be confirmed from a source, it stays **blank**, and the record
says why it is blank. A guessed species, a site name inferred from a folder name,
or a period derived from "it looks Roman" is worse than an empty field, because
the next reader cannot tell it was a guess.

Every metadata field carries provenance: *how* was this established?
(`from_publication`, `from_pride_metadata`, `derived_from_parquet`,
`personal_communication`, …). If you add a value, add its source.

### Never force a mapping

If a ZooMS concept has no honest equivalent in a vocabulary, we do not borrow a
term that means something similar-but-different. The worked example: MALDI-ToF has
**no retention time**, so we do not bind our `rt` column to the PSI-MS retention
time term, even though the column exists and the term exists. A wrong binding is
machine-readable misinformation.

Where nothing fits, propose a local `zooms:` term with a written justification.

### Never commit data

This repository holds code and specification only. No spectra, no `.raw`, no
`.mzML`, no `.parquet` — see `.gitignore`. Test fixtures must be synthetic or from
a published, licence-compatible source, and must be tiny.

### Never commit secrets

API keys and tokens are provisioned interactively and injected via environment
variables. Never a default in code, never a committed `.env`, never pasted into an
issue.

### Respect embargoes

Some datasets are unpublished or under embargo. Do not add a dataset identifier,
site name, or sample detail to a public file unless you are certain it is
already public.

---

## Proposing a vocabulary binding

Bindings live in `vocab/*.cv.yaml` as records, not bare strings:

```yaml
site_name:
  prefix: lado
  id: DiscoverySite
  label: Discovery Site
  source: "LADO v1.1 (doi:10.5281/zenodo.15477358)"
  status: provisional        # provisional | stable | local
  note: >
    Why this term and not a near neighbour; what it excludes.
```

When proposing one, please say:

1. **Which term**, with its full IRI, and where it is published.
2. **Why this term rather than the obvious alternatives** — including what it
   would wrongly assert if we used the near neighbour instead.
3. **Its licence**, and whether it is stable or still moving.
4. **Whether you are connected to the vocabulary** — not a problem at all, but
   worth stating.

Prefixes go in `vocab/prefixes.yaml`. Record namespace IRIs **exactly** as
published — including `http://` where that is what the vocabulary uses. An IRI is
an identifier, not a URL to fetch; "upgrading" it to `https://` silently creates a
different, non-matching identifier.

---

## Reporting a format that does not load

Please include:

- The **instrument and software** that produced it (e.g. Bruker flex series,
  flexAnalysis export).
- A **small excerpt** — the first ~20 lines of a text export, or the file header.
  Do not attach a full dataset, and do not attach anything unpublished.
- What the columns **mean**, if it is not obvious.
- Whether the data is **already peak-picked** or is a profile spectrum. This one
  matters more than it looks: silently treating profile data as centroided
  reintroduces continuum into downstream matching.

---

## Pull requests

- Branch from `main`; keep one logical change per PR.
- Explain **why**, not just what. For a binding or schema change, the reasoning is
  the substance of the review.
- Schema changes must be **additive** unless there is a version bump — existing
  readers must not break.
- Run the tests. Add one for anything with behaviour.
- The specification and the code must move together: if you change a schema, change
  `vocab/` and `spec/` in the same PR.

## Attribution

Contributors are credited in `CITATION.cff`. If you contribute archaeological
context or vocabulary work that involves real scholarly judgement, say so in the
PR and we will make sure the credit reflects it — that work is authorship, not
just a data entry task.
