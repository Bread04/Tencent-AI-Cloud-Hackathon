"""Draw the three simulated Property Damage photos in data/photos/ (a rear car seat with a dark stain).

They are illustrations, not real photos, and each carries a small "SIMULATED" mark. The three differ only in what the
Image Analysis demo needs them to show: the genuine one, the old one (a faded print, taken before the trip) and the
synthetic one (too smooth, with a texture that repeats). Capture times live in the .json beside each file.

    uv run python -m scripts.make_demo_photos
"""

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

OUT = Path(__file__).resolve().parents[1] / "data" / "photos"
W, H = 640, 420


def cabin(rng: random.Random) -> Image.Image:
    """A rear seat seen from the open door: door-frame shadow, backrest, cushion with stitching, a seat belt."""
    img = Image.new("RGB", (W, H), (58, 62, 70))
    d = ImageDraw.Draw(img)
    for y in range(H):  # the floor and door sill fall away to dark at the bottom
        shade = int(34 + 30 * (1 - y / H))
        d.line([(0, y), (W, y)], fill=(shade, shade + 2, shade + 8))
    d.polygon([(0, 0), (150, 0), (90, H), (0, H)], fill=(24, 26, 31))  # the door frame
    d.rounded_rectangle([120, 70, 600, 250], radius=40, fill=(92, 88, 84))  # backrest
    d.rounded_rectangle([90, 235, 620, 370], radius=34, fill=(104, 100, 95))  # cushion
    for x in range(180, 600, 86):  # stitched panels on the backrest
        d.line([(x, 84), (x, 238)], fill=(70, 67, 64), width=3)
        for y in range(90, 236, 14):
            d.line([(x - 1, y), (x - 1, y + 6)], fill=(128, 123, 116), width=1)
    d.line([(112, 300), (610, 300)], fill=(78, 75, 71), width=3)  # the seam between the cushion's two panels
    d.polygon([(470, 60), (508, 60), (560, 250), (518, 250)], fill=(30, 31, 34))  # seat belt
    d.rectangle([505, 236, 535, 262], fill=(150, 152, 158))  # its buckle
    return img


def grain(img: Image.Image, rng: random.Random, strength: int) -> Image.Image:
    """Fabric grain: random speckle, so the surface reads as upholstery and not as flat colour."""
    noise = Image.effect_noise((W, H), strength).convert("RGB")
    return Image.blend(img, ImageChops_add(img, noise), 0.35)


def ImageChops_add(a: Image.Image, b: Image.Image) -> Image.Image:
    from PIL import ImageChops

    return ImageChops.overlay(a, b)


def stain(img: Image.Image, rng: random.Random) -> Image.Image:
    """A dark, damp-looking patch on the cushion: a few overlapping blobs, soft at the edge, with a wet sheen."""
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    cx, cy = 330, 305
    for _ in range(9):
        rx, ry = rng.randint(26, 62), rng.randint(16, 34)
        ox, oy = rng.randint(-46, 46), rng.randint(-14, 16)
        d.ellipse([cx + ox - rx, cy + oy - ry, cx + ox + rx, cy + oy + ry], fill=rng.randint(170, 255))
    mask = mask.filter(ImageFilter.GaussianBlur(7))
    dark = Image.new("RGB", (W, H), (38, 30, 27))
    out = Image.composite(dark, img, mask.point(lambda v: int(v * 0.85)))
    sheen = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sheen).ellipse([cx - 40, cy - 18, cx + 10, cy - 2], fill=120)
    sheen = sheen.filter(ImageFilter.GaussianBlur(6))
    return Image.composite(Image.new("RGB", (W, H), (150, 140, 130)), out, ImageChops_multiply(sheen, mask))


def ImageChops_multiply(a: Image.Image, b: Image.Image) -> Image.Image:
    from PIL import ImageChops

    return ImageChops.multiply(a, b)


def mark(img: Image.Image) -> Image.Image:
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 13)
    except OSError:
        font = ImageFont.load_default()
    d.text((12, H - 24), "SIMULATED PHOTO  |  Waypoint demo", fill=(210, 214, 222), font=font)
    return img


def genuine() -> Image.Image:
    rng = random.Random(11)
    img = stain(grain(cabin(rng), rng, 40), rng).filter(ImageFilter.GaussianBlur(0.6))
    return mark(img)


def old() -> Image.Image:
    """The same seat on an old, faded print: warm, washed out, with a vignette and the stain half dried."""
    rng = random.Random(11)
    img = stain(grain(cabin(rng), rng, 40), rng)
    img = ImageOps.colorize(ImageOps.grayscale(img), black=(48, 38, 28), white=(236, 220, 190))
    img = Image.blend(img, Image.new("RGB", (W, H), (214, 196, 160)), 0.18).filter(ImageFilter.GaussianBlur(1.1))
    vignette = Image.radial_gradient("L").resize((W, H)).point(lambda v: 255 - int(v * 0.55))
    return mark(Image.composite(img, Image.new("RGB", (W, H), (30, 22, 14)), vignette))


def synthetic() -> Image.Image:
    """Too clean: no grain, over-saturated, and the same tile repeated across the seat, as a generated image can be."""
    rng = random.Random(11)
    base = stain(cabin(rng), rng)
    tile = base.crop((200, 100, 296, 196)).filter(ImageFilter.GaussianBlur(2))
    for x in range(120, 540, 96):
        base.paste(tile, (x, 100))
    img = ImageEnhance.Color(base.filter(ImageFilter.SMOOTH_MORE).filter(ImageFilter.GaussianBlur(1.2))).enhance(1.6)
    return mark(Image.blend(img, Image.new("RGB", (W, H), (60, 90, 150)), 0.1))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, make in {"seat-stain.png": genuine, "seat-stain-old.png": old, "seat-stain-synthetic.png": synthetic}.items():
        make().save(OUT / name, optimize=True)
        print(name, (OUT / name).stat().st_size, "bytes")
