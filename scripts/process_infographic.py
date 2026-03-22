#!/usr/bin/env python3
"""Post-process NotebookLM infographic: remove watermark and resize for Instagram."""

import sys
from pathlib import Path

from PIL import Image


# NotebookLM watermark sits in the bottom-right corner
WATERMARK_HEIGHT = 55  # pixels to crop from bottom
WATERMARK_WIDTH = 200  # pixels to cover from right side


def remove_watermark(image_path, output_path=None):
    """Remove NotebookLM watermark by painting over it with nearby pixels."""
    img = Image.open(image_path)
    output_path = output_path or image_path

    # Sample a strip just above the watermark area to get the background
    w, h = img.size
    # Crop a 1px tall strip just above the watermark zone on the right side
    sample_y = h - WATERMARK_HEIGHT - 1
    sample_strip = img.crop((w - WATERMARK_WIDTH, sample_y, w, sample_y + 1))

    # Stretch that strip down to fill the watermark area
    fill = sample_strip.resize((WATERMARK_WIDTH, WATERMARK_HEIGHT))
    img.paste(fill, (w - WATERMARK_WIDTH, h - WATERMARK_HEIGHT))

    img.save(output_path, quality=95)
    print(f"Watermark removed: {output_path}")
    return output_path


INSTAGRAM_MAX_SIZE = 1080


def resize_for_instagram(image_path, output_path=None):
    """Resize to Instagram max dimensions and convert to JPEG for smaller file size."""
    img = Image.open(image_path)
    output_path = output_path or image_path
    w, h = img.size

    if w > INSTAGRAM_MAX_SIZE or h > INSTAGRAM_MAX_SIZE:
        ratio = min(INSTAGRAM_MAX_SIZE / w, INSTAGRAM_MAX_SIZE / h)
        new_size = (int(w * ratio), int(h * ratio))
        img = img.resize(new_size, Image.LANCZOS)
        print(f"Resized: {w}x{h} -> {new_size[0]}x{new_size[1]}")

    # Save as JPEG for smaller file size
    jpeg_path = Path(output_path).with_suffix(".jpg")
    if img.mode == "RGBA":
        img = img.convert("RGB")
    img.save(jpeg_path, "JPEG", quality=90)
    print(f"Saved as JPEG: {jpeg_path}")

    # Remove the original PNG if we created a new JPEG
    if str(jpeg_path) != str(output_path) and Path(output_path).exists():
        Path(output_path).unlink()
        print(f"Removed original: {output_path}")

    return str(jpeg_path)


def process_infographic(image_path, output_path=None):
    """Full post-processing pipeline for infographic images."""
    output_path = output_path or image_path

    remove_watermark(image_path, output_path)
    final_path = resize_for_instagram(output_path)

    img = Image.open(final_path)
    size_kb = Path(final_path).stat().st_size / 1024
    print(f"Final image: {img.size[0]}x{img.size[1]}, {size_kb:.0f} KB")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/process_infographic.py <image_path> [output_path]")
        sys.exit(1)

    image_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    if not Path(image_path).exists():
        print(f"Error: File not found: {image_path}")
        sys.exit(1)

    process_infographic(image_path, output_path)
