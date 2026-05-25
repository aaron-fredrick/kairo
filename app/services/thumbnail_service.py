"""
Thumbnail generation service.

Supported inputs:
- Images (JPEG, PNG, GIF, WEBP, BMP, TIFF, etc.) — direct Pillow resize.
- PDF — first page rendered via pdf2image (requires poppler on PATH).
- DOCX / PPTX / XLSX — first page/sheet rendered; falls back to generic icon.
- Everything else — a generic file-type icon.

Output sizes (width × height, JPEG):
- sm : 160 × 160
- md : 480 × 480
- lg : 960 × 960
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import os
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError

from app.core.logging import get_logger

logger = get_logger(__name__)

THUMBNAIL_SIZES: dict[str, Tuple[int, int]] = {
    "sm": (160, 160),
    "md": (480, 480),
    "lg": (960, 960),
}

IMAGE_MIME_PREFIXES = ("image/",)
PDF_MIME = "application/pdf"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


def _make_generic_thumbnail(label: str, size: Tuple[int, int]) -> Image.Image:
    """Render a simple coloured tile with the file extension label."""
    img = Image.new("RGB", size, color=(45, 55, 72))
    draw = ImageDraw.Draw(img)
    text = label.upper()[:6]
    try:
        font = ImageFont.truetype("arial.ttf", size=max(16, size[0] // 6))
    except (OSError, IOError):
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    draw.text(
        ((size[0] - text_w) / 2, (size[1] - text_h) / 2),
        text,
        fill=(160, 174, 192),
        font=font,
    )
    return img


def _source_image_from_pdf(data: bytes) -> Optional[Image.Image]:
    try:
        from pdf2image import convert_from_bytes  # type: ignore
        pages = convert_from_bytes(data, first_page=1, last_page=1, dpi=72)
        return pages[0] if pages else None
    except Exception as exc:
        logger.warning("pdf2image failed: %s", exc)
        return None


def _source_image_from_docx(data: bytes) -> Optional[Image.Image]:
    """
    Attempt to extract the first embedded image from a DOCX file.
    Falls back to None so the caller uses a generic thumbnail.
    """
    try:
        import zipfile
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            image_names = [
                n for n in z.namelist()
                if n.startswith("word/media/") and not n.endswith("/")
            ]
            if not image_names:
                return None
            image_names.sort()
            with z.open(image_names[0]) as img_file:
                return Image.open(io.BytesIO(img_file.read())).copy()
    except Exception as exc:
        logger.warning("DOCX image extraction failed: %s", exc)
        return None


def _get_source_image(data: bytes, mime_type: str, extension: str) -> Image.Image:
    """Return the best-effort source PIL image for the given file."""
    if any(mime_type.startswith(p) for p in IMAGE_MIME_PREFIXES):
        try:
            return Image.open(io.BytesIO(data)).convert("RGB")
        except UnidentifiedImageError:
            pass

    if mime_type == PDF_MIME:
        img = _source_image_from_pdf(data)
        if img:
            return img.convert("RGB")

    if mime_type == DOCX_MIME:
        img = _source_image_from_docx(data)
        if img:
            return img.convert("RGB")

    return _make_generic_thumbnail(extension, (960, 960))


def _generate_thumbnail_bytes(source: Image.Image, size: Tuple[int, int]) -> Tuple[bytes, str]:
    """Resize *source* to fit within *size*, return (jpeg_bytes, sha256_hex)."""
    thumb = source.copy()
    thumb.thumbnail(size, Image.LANCZOS)
    buffer = io.BytesIO()
    thumb.save(buffer, format="JPEG", quality=85, optimize=True)
    raw = buffer.getvalue()
    digest = hashlib.sha256(raw).hexdigest()
    return raw, digest


async def generate_thumbnails(
    data: bytes,
    mime_type: str,
    extension: str,
) -> dict[str, Tuple[bytes, str]]:
    """
    Run thumbnail generation in a thread-pool executor to avoid blocking the
    event loop.  Returns a dict keyed by size label:
        { "sm": (jpeg_bytes, sha256), "md": ..., "lg": ... }
    """
    loop = asyncio.get_event_loop()

    def _blocking() -> dict[str, Tuple[bytes, str]]:
        source = _get_source_image(data, mime_type, extension)
        return {
            label: _generate_thumbnail_bytes(source, size)
            for label, size in THUMBNAIL_SIZES.items()
        }

    return await loop.run_in_executor(None, _blocking)
