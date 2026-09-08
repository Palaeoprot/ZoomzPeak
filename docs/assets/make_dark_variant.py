"""
Generate the dark-theme variant of the ZoomzPeak mark.

The mark is a single flat blue (#002EF9) on a transparent background, with all
antialiasing carried in the alpha channel rather than in blended RGB. That means
the recolour is exact: replace every pixel's RGB with the target colour and keep
its alpha untouched. No resampling, no edge artefacts, no halo.

Why a variant is needed at all:

    #002EF9 on GitHub light (#FFFFFF)  ->  7.61:1
    #002EF9 on GitHub dark  (#0D1117)  ->  2.49:1   below the 3:1 WCAG AA
                                                    threshold for graphics
    #7C9BFF on GitHub dark  (#0D1117)  ->  7.20:1

#7C9BFF was chosen so the dark variant sits at roughly the same contrast against
its background as the original does against white. The mark then carries equal
visual weight in either theme rather than looking timid in one of them, and the
hue is preserved so it still reads as the same blue.

    python docs/assets/make_dark_variant.py
"""

from pathlib import Path

from PIL import Image

SRC = Path(__file__).parent / "mark1.png"
OUT = Path(__file__).parent / "mark1-dark.png"

# Lightened blue for dark backgrounds. Same hue family as the original.
DARK_THEME_COLOUR = (0x7C, 0x9B, 0xFF)

GITHUB_DARK = (0x0D, 0x11, 0x17)
GITHUB_LIGHT = (0xFF, 0xFF, 0xFF)


def relative_luminance(colour):
    """WCAG 2.1 relative luminance."""

    def channel(value):
        value /= 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in colour)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a, b):
    la, lb = relative_luminance(a), relative_luminance(b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def main():
    source = Image.open(SRC).convert("RGBA")
    alpha = source.getchannel("A")

    recoloured = Image.new("RGBA", source.size, DARK_THEME_COLOUR + (0,))
    recoloured.putalpha(alpha)
    recoloured.save(OUT, optimize=True)

    print(f"wrote {OUT.name}  {source.size[0]}x{source.size[1]}  {OUT.stat().st_size:,} bytes")
    print(
        f"  contrast on GitHub dark:  {contrast_ratio(DARK_THEME_COLOUR, GITHUB_DARK):.2f}:1"
    )
    print(
        f"  (original on light:       {contrast_ratio((0x00, 0x2E, 0xF9), GITHUB_LIGHT):.2f}:1)"
    )


if __name__ == "__main__":
    main()
