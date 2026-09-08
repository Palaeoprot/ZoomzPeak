# Visual assets

## Current state

`mark1.png` -- **option 2, "Collagen Fragment"**: spectrum peaks rising into an
abstract bone/tooth fragment, with the ZoomzPeak wordmark beneath. Chosen
2026-09-08. This is the project mark, used in the README.

    517 x 370, RGBA with a transparent background, flat colour, 81 KB

`mark1-dark.png` -- the same mark for dark backgrounds, in a lightened blue.
The README serves them through a `<picture>` element, so GitHub swaps them on
`prefers-color-scheme` automatically.

### Why the dark variant exists, and how it was made

Measured, not guessed:

| | contrast |
|---|---|
| `#002EF9` on GitHub light `#FFFFFF` | **7.61:1** |
| `#002EF9` on GitHub dark `#0D1117` | **2.49:1** -- below the 3:1 WCAG AA threshold for graphics |
| `#7C9BFF` on GitHub dark `#0D1117` | **7.20:1** |

`#7C9BFF` was chosen so the dark variant sits at roughly the same contrast
against its background as the original does against white. The mark then carries
equal visual weight in either theme rather than looking timid in one, and the
hue is preserved so it still reads as the same blue.

The recolour is exact rather than a filter. All antialiasing in the source lives
in the alpha channel, not in blended RGB, so replacing every pixel's RGB and
keeping its alpha produces no halo, no resampling and no edge artefacts -- the
two files have bit-identical alpha channels. Regenerate with:

```bash
python docs/assets/make_dark_variant.py
```

It supersedes the four-option exploration comp sheet that briefly lived here as
`mark.png`, which was removed on 2026-09-08.

### What is still wanted

The mark is usable as it stands. These would make it complete:

- [ ] `logo.svg` -- vector source. A raster lockup cannot be scaled for print,
      and 517 px is thin for a paper figure.
- [ ] `logo-mono.svg` -- single-colour black and white, for print and embossing
- [x] ~~Dark-mode variant~~ -- done, `mark1-dark.png` (above)
- [ ] `favicon.ico` -- 16/32/48 px, mark only, no wordmark
- [ ] `mark-only.svg` -- the bone/peaks glyph without the wordmark, for places
      too small for the lockup
- [ ] Provenance recorded below

## Notes for whoever draws the final version

- **Flatten the gradient.** The comps use a blue-to-blue gradient. It will not
  survive small sizes, single-colour printing, or greyscale.
- **Watch the peak strokes.** The four peaks to the left of the bone thin toward
  the left edge and are the part most likely to fill in or vanish at 16 px. Be
  willing to drop to three peaks in the favicon variant — the concept survives it;
  illegibility does not.
- The bone silhouette itself is a solid mass with no internal negative space, which
  is why this option scales better than the alternatives on the sheet.

## Provenance

**To be completed.** If these comps were generated with an AI tool, record which
one here. For a public, citable, CC-licensed project the origin of the visual
identity should be on the record — it bears on what the project can assert about
ownership.

## Relationship to mzPeak

The mark takes visual inspiration from
[mzPeak](https://www.mzpeak.org/), a HUPO-PSI standard, since `mzPeakMS-ZooMS` is
defined as a profile of that format.

HUPO-PSI have invited palaeoproteomics involvement, and the mark is being raised
with them directly. The intent is a *family resemblance* that signals the technical
relationship — not a derivation that could be read as HUPO-PSI endorsement of a
specification they have not reviewed. Record their response here once received.

## Licence — read this before reusing

The ZoomzPeak name and logo are **not** covered by the repository's Apache-2.0 or
CC-BY-4.0 licences. All rights reserved. See [`LICENSE-SPEC`](../../LICENSE-SPEC).

You may use the mark to refer to this project. You may not use it as the identity
of a fork, or in any way suggesting endorsement by or affiliation with this
project.
