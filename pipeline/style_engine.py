"""
style_engine.py
---------------
Three high-end visual styles for the FB-Quotes project:

1. The "Big Left"        : Bold, heavy fonts stacked on the left (Magazine style).
2. The "Cinematic Sub"   : Small clean text at bottom + subtle vignette (Film style).
3. The "Giant Invert"    : Massive XOR-inverted text (Abstract vibe style).
"""

import random
import logging
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
import numpy as np
import requests

logger = logging.getLogger(__name__)

FONT_PATH = Path(__file__).parent / "assets" / "Outfit-Bold.ttf"
OUTPUT_DIR = Path("tmp_assets")

# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Loads Outfit-Bold or falls back to system fonts / download."""
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

    # 3. Try to download a font if all else fails
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

    # 4. Last resort
    logger.warning("!!! CRITICAL: No TTF fonts found. Using tiny default.")
    return ImageFont.load_default()


def _canonical_size(img: Image.Image, target_w: int = 1080) -> Image.Image:
    """Resize to FB-friendly 1080-wide portrait (4:5 ratio)."""
    w, h = img.size
    ratio = target_w / w
    new_h = int(h * ratio)
    new_h = max(new_h, int(target_w * 1.25))
    img = img.resize((target_w, new_h), Image.LANCZOS)
    target_h = int(target_w * 1.25) # 1350
    if img.height > target_h:
        top = (img.height - target_h) // 2
        img = img.crop((0, top, target_w, top + target_h))
    return img


def _wrap_text(text: str, font, max_width: int) -> list[str]:
    """Naive word-wrap."""
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


# ── Style 1: The Big Left (Magazine) ──────────────────────────────────────────

def style_big_left(img_path: Path, quote: str, out_path: Path) -> Path:
    """Bold, heavy fonts stacked on the left."""
    base = _canonical_size(Image.open(img_path).convert("RGB"))
    w, h = base.size
    
    # Massive font for the left stack
    font_size = int(w * 0.12) # ~130px
    font = _load_font(font_size)
    
    # Wrap to a narrow column on the left
    lines = _wrap_text(quote, font, int(w * 0.6))
    
    # Draw on overlay for legibility
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Subtle gradient/shadow from left
    for x in range(int(w * 0.7)):
        alpha = int(180 * (1 - (x / (w * 0.7))))
        draw.line([(x, 0), (x, h)], fill=(0, 0, 0, alpha))
        
    y_start = int(h * 0.2)
    line_h = font_size + 10
    
    for i, line in enumerate(lines):
        draw.text((int(w * 0.08), y_start + i * line_h), 
                  line.upper(), font=font, fill=(255, 255, 255, 255))
        
    final = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    final.save(out_path, "JPEG", quality=92)
    return out_path


# ── Style 2: Cinematic Subtitle (Film) ────────────────────────────────────────

def style_cinematic_sub(img_path: Path, quote: str, out_path: Path) -> Path:
    """Small clean text at bottom + subtle vignette."""
    base = _canonical_size(Image.open(img_path).convert("RGB"))
    w, h = base.size
    
    # Subtle vignette / grey layer
    vignette = Image.new("RGBA", base.size, (20, 20, 25, 60)) # Grey tint
    base = Image.alpha_composite(base.convert("RGBA"), vignette).convert("RGB")
    
    # Draw logic
    draw = ImageDraw.Draw(base)
    font_size = int(w * 0.04) # ~43px (small)
    font = _load_font(font_size)
    
    # Wrap for center bottom
    lines = _wrap_text(quote, font, int(w * 0.8))
    
    line_h = font_size + 15
    total_h = line_h * len(lines)
    y_start = int(h * 0.88) - total_h
    
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((w - tw) // 2, y_start + i * line_h), 
                  line, font=font, fill=(255, 255, 255, 230))
        
    base.save(out_path, "JPEG", quality=92)
    return out_path


# ── Style 3: Giant Invert (Vibe) ─────────────────────────────────────────────

def style_giant_invert(img_path: Path, quote: str, out_path: Path) -> Path:
    """Massive XOR-inverted text."""
    base = _canonical_size(Image.open(img_path).convert("RGB"))
    w, h = base.size
    
    # Massive font
    font_size = int(w * 0.20) # ~216px (HUGE)
    if len(quote) > 15: font_size = int(w * 0.14)
    font = _load_font(font_size)
    
    lines = _wrap_text(quote, font, int(w * 0.9))
    
    # Render text to mask
    mask = Image.new("L", base.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    
    line_h = font_size + 5
    total_h = line_h * len(lines)
    y_start = (h - total_h) // 2
    
    for i, line in enumerate(lines):
        bbox = mask_draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        mask_draw.text(((w - tw) // 2, y_start + i * line_h), 
                        line.lower(), font=font, fill=255)
        
    # XOR Inversion
    base_arr = np.array(base)
    mask_arr = np.array(mask)
    text_px = mask_arr > 128
    
    res_arr = base_arr.copy()
    # Invert RGB channels
    res_arr[text_px] = 255 - base_arr[text_px]
    
    final = Image.fromarray(res_arr)
    final.save(out_path, "JPEG", quality=92)
    return out_path


# ── Dispatcher ────────────────────────────────────────────────────────────────

STYLES = {
    "BigLeft": style_big_left,
    "CinematicSub": style_cinematic_sub,
    "GiantInvert": style_giant_invert,
}

def apply_random_style(img_path: Path, quote: str, run_id: str, style_key: str = None) -> Path:
    """
    Applies the specified visual style, or selects one based on guidelines
    if none is provided.
    """
    if not style_key:
        char_count = len(quote)
        if char_count < 15:
            style_key = "GiantInvert"
        elif char_count <= 40:
            style_key = "BigLeft"
        else:
            style_key = "CinematicSub"
    
    style_fn = STYLES[style_key]
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"final_{run_id}_{style_key}.jpg"
    
    logger.info("🎨 Applying Style: %s", style_key)
    result = style_fn(img_path, quote, out_path)
    return result
