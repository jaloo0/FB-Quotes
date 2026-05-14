"""
style_engine.py
---------------
Applies one of three high-end visual styles to (image_path, quote_text):

  Style A – "Inverted Cursor"   : XOR-inverted text colour per pixel
  Style B – "Subject Sandwich"  : rembg subject isolation, text behind hero
  Style C – "Frosted Depth"     : blurred BG + sharp subject, text overlay

Returns the path to the finished composite image.
"""

import random
import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
import numpy as np
import requests

logger = logging.getLogger(__name__)

FONT_PATH = Path(__file__).parent / "assets" / "Outfit-Bold.ttf"
OUTPUT_DIR = Path("tmp_assets")

# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    # 1. Try preferred custom font
    if FONT_PATH.exists():
        try:
            return ImageFont.truetype(str(FONT_PATH), size)
        except Exception:
            pass

    # 2. Try common system fonts with absolute paths
    fallbacks = [
        "C:\\Windows\\Fonts\\arialbd.ttf", # Windows Bold
        "C:\\Windows\\Fonts\\arial.ttf",   # Windows
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", # Linux
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "arial.ttf",
        "DejaVuSans.ttf"
    ]
    
    for f in fallbacks:
        try:
            return ImageFont.truetype(f, size)
        except Exception:
            continue

    # 3. Try to download a font if all else fails (GitHub Actions fallback)
    try:
        FONT_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not FONT_PATH.exists():
            logger.info("Downloading fallback font...")
            url = "https://github.com/google/fonts/raw/main/ofl/outfit/Outfit%5Bwght%5D.ttf"
            r = requests.get(url, timeout=30)
            with open(FONT_PATH, "wb") as f:
                f.write(r.content)
        return ImageFont.truetype(str(FONT_PATH), size)
    except Exception as e:
        logger.warning("Font download failed: %s", e)

    # 4. Last resort (will be very small and not scalable)
    logger.warning("!!! CRITICAL: No TTF fonts found. Text will be 10px and likely INVISIBLE on high-res images.")
    return ImageFont.load_default()


def _canonical_size(img: Image.Image, target_w: int = 1080) -> Image.Image:
    """Resize to FB-friendly 1080-wide portrait while preserving ratio."""
    w, h = img.size
    ratio = target_w / w
    new_h = int(h * ratio)
    # Ensure at least 1080 tall (4:5 Facebook feed minimum)
    new_h = max(new_h, int(target_w * 1.25))
    img = img.resize((target_w, new_h), Image.LANCZOS)
    # Centre-crop to exactly 1080×1350 (4:5)
    target_h = int(target_w * 1.25)
    if img.height > target_h:
        top = (img.height - target_h) // 2
        img = img.crop((0, top, target_w, top + target_h))
    return img


def _text_position(img_size: tuple[int, int]) -> tuple[int, int]:
    """Centre-bottom third of the image."""
    w, h = img_size
    return (w // 2, int(h * 0.72))


def _wrap_text(text: str, font, max_width: int) -> list[str]:
    """Naive word-wrap for Pillow."""
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        current = ""
        dummy_img = Image.new("RGB", (1, 1))
        draw = ImageDraw.Draw(dummy_img)
        for word in words:
            test = f"{current} {word}".strip()
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] > max_width and current:
                lines.append(current)
                current = word
            else:
                current = test
        if current:
            lines.append(current)
    return lines


def _draw_text_centered(
    draw: ImageDraw.Draw,
    lines: list[str],
    font,
    center_xy: tuple[int, int],
    fill,
    stroke_fill=None,
    stroke_width: int = 2,
) -> None:
    cx, cy = center_xy
    
    # Try to get line height from a sample bbox
    try:
        sample_bbox = draw.textbbox((0, 0), "Ay|", font=font)
        line_h = (sample_bbox[3] - sample_bbox[1]) + 15
    except Exception:
        line_h = 40
    
    total_h = line_h * len(lines)
    start_y = cy - total_h // 2

    logger.info("Drawing %d lines of text at %s (line_h %d)", len(lines), center_xy, line_h)

    # DEBUG WATERMARK
    draw.text((10, 10), "MODIFIED BY ENGINE", fill=(255, 0, 0))

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = cx - text_w // 2
        y = start_y + i * line_h
        if stroke_fill:
            draw.text((x, y), line, font=font, fill=stroke_fill,
                      stroke_width=stroke_width, stroke_fill=stroke_fill)
        draw.text((x, y), line, font=font, fill=fill)


# ── Style A: Inverted Cursor ──────────────────────────────────────────────────

def style_a_inverted_cursor(img_path: Path, quote: str, out_path: Path) -> Path:
    """
    Render text on a transparent mask, then XOR-invert text pixels
    against the background so text is always legible.
    """
    base = _canonical_size(Image.open(img_path).convert("RGB"))
    font_size = max(48, base.width // 18)
    font = _load_font(font_size)

    lines = _wrap_text(quote, font, int(base.width * 0.80))
    center = _text_position(base.size)

    # --- render text on black mask ---
    text_mask = Image.new("L", base.size, 0)
    mask_draw = ImageDraw.Draw(text_mask)
    line_h = font_size + 8
    total_h = line_h * len(lines)
    start_y = center[1] - total_h // 2
    cx = center[0]
    for i, line in enumerate(lines):
        bbox = mask_draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = cx - tw // 2
        y = start_y + i * line_h
        mask_draw.text((x, y), line, font=font, fill=255)

    # --- XOR inversion per pixel ---
    base_arr = np.array(base, dtype=np.uint8)
    mask_arr = np.array(text_mask, dtype=np.uint8)
    # Invert base pixels where text mask is white
    text_px = mask_arr > 128
    result_arr = base_arr.copy()
    result_arr[text_px] = 255 - base_arr[text_px]

    result = Image.fromarray(result_arr, "RGB")

    # --- light semi-transparent backdrop for readability ---
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    pad = 20
    box_top = start_y - pad
    box_bot = start_y + total_h + pad
    ov_draw.rectangle(
        [(cx - base.width // 2, box_top), (cx + base.width // 2, box_bot)],
        fill=(0, 0, 0, 60),
    )
    composite = Image.alpha_composite(result.convert("RGBA"), overlay).convert("RGB")

    composite.save(out_path, "JPEG", quality=92)
    logger.info("Style A saved: %s", out_path)
    return out_path


# ── Style B: Subject Sandwich ─────────────────────────────────────────────────

def style_b_subject_sandwich(img_path: Path, quote: str, out_path: Path) -> Path:
    """
    Layers: background → text → isolated subject on top.
    Uses rembg to remove background from the subject.
    Falls back to Style C if rembg is unavailable.
    """
    try:
        from rembg import remove as rembg_remove  # pip install rembg
    except ImportError:
        logger.warning("rembg not installed – falling back to Style C.")
        return style_c_frosted_depth(img_path, quote, out_path)

    base = _canonical_size(Image.open(img_path).convert("RGB"))
    font_size = max(52, base.width // 16)
    font = _load_font(font_size)

    # --- isolate subject ---
    subject_rgba = rembg_remove(base.convert("RGBA"))

    # --- compose background (slightly darkened) ---
    bg = base.copy().convert("RGBA")
    dark_overlay = Image.new("RGBA", base.size, (0, 0, 0, 100))
    bg = Image.alpha_composite(bg, dark_overlay)

    # --- draw text on background ---
    lines = _wrap_text(quote, font, int(base.width * 0.82))
    center = _text_position(base.size)
    text_layer = bg.copy()
    draw = ImageDraw.Draw(text_layer)
    _draw_text_centered(
        draw, lines, font,
        center_xy=center,
        fill=(255, 255, 255, 240),
        stroke_fill=(0, 0, 0, 255),
        stroke_width=3,
    )

    # --- place subject on top ---
    final = Image.alpha_composite(text_layer, subject_rgba)
    final.convert("RGB").save(out_path, "JPEG", quality=92)
    logger.info("Style B saved: %s", out_path)
    return out_path


# ── Style C: Frosted Depth ────────────────────────────────────────────────────

def style_c_frosted_depth(img_path: Path, quote: str, out_path: Path) -> Path:
    """
    Blurs background (Gaussian radius ≈ 12 → ~40% blur) but keeps
    subject sharp via a luminance-driven focus mask.
    """
    base = _canonical_size(Image.open(img_path).convert("RGB"))
    font_size = max(52, base.width // 16)
    font = _load_font(font_size)

    # --- blur the full frame ---
    blurred = base.filter(ImageFilter.GaussianBlur(radius=12))

    # --- create a simple radial focus mask (centre stays sharp) ---
    w, h = base.size
    mask = Image.new("L", (w, h), 0)
    mask_draw = ImageDraw.Draw(mask)
    # Large ellipse in centre = sharp zone
    margin_x, margin_y = int(w * 0.15), int(h * 0.10)
    mask_draw.ellipse(
        [(margin_x, margin_y), (w - margin_x, h - margin_y)],
        fill=255,
    )
    mask = mask.filter(ImageFilter.GaussianBlur(radius=80))

    # --- composite: blurred where mask=0, sharp where mask=255 ---
    depth = Image.composite(base, blurred, mask)

    # --- frosted glass text bar ---
    bar_h = int(h * 0.28)
    bar_top = int(h * 0.62)
    bar_region = depth.crop((0, bar_top, w, bar_top + bar_h))
    bar_blurred = bar_region.filter(ImageFilter.GaussianBlur(radius=20))

    bar_overlay = Image.new("RGBA", (w, bar_h), (10, 10, 20, 160))
    bar_comp = Image.alpha_composite(bar_blurred.convert("RGBA"), bar_overlay)
    depth.paste(bar_comp.convert("RGB"), (0, bar_top))

    # --- draw text ---
    lines = _wrap_text(quote, font, int(w * 0.82))
    center = (w // 2, bar_top + bar_h // 2)
    draw = ImageDraw.Draw(depth)
    _draw_text_centered(
        draw, lines, font,
        center_xy=center,
        fill=(255, 255, 255),
        stroke_fill=(0, 0, 0),
        stroke_width=2,
    )

    depth.save(out_path, "JPEG", quality=92)
    logger.info("Style C saved: %s", out_path)
    return out_path


# ── Dispatcher ────────────────────────────────────────────────────────────────

STYLES = {
    "A": style_a_inverted_cursor,
    "B": style_b_subject_sandwich,
    "C": style_c_frosted_depth,
}


def apply_random_style(img_path: Path, quote: str, run_id: str) -> Path:
    """Pick a random style, apply it, return output path."""
    available_styles = list(STYLES.keys())
    style_key = random.choice(available_styles)
    
    # Check if rembg is available for Style B
    try:
        import rembg # noqa: F401
    except ImportError:
        if style_key == "B":
            logger.info("Style B chosen but rembg missing. Forcing Style A or C.")
            style_key = random.choice(["A", "C"])

    style_fn = STYLES[style_key]
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"final_{run_id}_style{style_key}.jpg"
    
    logger.info("🎨 APPLYING STYLE: %s", style_key)
    
    result_path = style_fn(img_path, quote, out_path)
    
    # Final watermark on the finished file
    try:
        final_img = Image.open(result_path).convert("RGB")
        d = ImageDraw.Draw(final_img)
        # Use a big red box for the watermark so it's impossible to miss
        d.rectangle([0, 0, 300, 40], fill=(255, 0, 0))
        d.text((10, 10), f"STYLE {style_key} ACTIVE", fill=(255, 255, 255))
        final_img.save(result_path, "JPEG", quality=95)
    except Exception as e:
        logger.error("Watermark failed: %s", e)
        
    return result_path
