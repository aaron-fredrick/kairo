"""
Thumbnail generation service.

Supported inputs:
  - Images (JPEG, PNG, GIF, WEBP, BMP, TIFF, …) — direct Pillow resize.
  - PDF — first page rendered via pdf2image (requires poppler on PATH).
  - DOCX — first embedded image extracted.
  - Everything else — a generic labelled tile.

Output sizes (longest edge):
  - 128px   → suffix _128
  - 512px   → suffix _512
  - 1024px  → suffix _1024

Output format: WebP (lossless for palette images, quality=85 otherwise).
Output path:   data/thumbnails/sha256/<2>/<2>/<blob_hash>_<size>.webp

EXIF data is always stripped — no GPS coordinates or device metadata
are ever persisted in thumbnail output.
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import os
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Size label → maximum longest-edge dimension (square bounding box)
THUMBNAIL_SIZES: dict[str, int] = {
    "128": 128,
    "512": 512,
    "1024": 1024,
}

IMAGE_MIME_PREFIXES = ("image/",)
PDF_MIME = "application/pdf"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def thumbnail_rel_path(blob_hash: str, size_label: str) -> str:
    """Return the provider-relative path for a thumbnail."""
    return os.path.join(
        "sha256", blob_hash[:2], blob_hash[2:4],
        f"{blob_hash}_{size_label}.webp",
    )


def thumbnail_abs_path(blob_hash: str, size_label: str) -> str:
    return os.path.join(settings.THUMBNAIL_DIR, thumbnail_rel_path(blob_hash, size_label))


def thumbnail_url(blob_hash: str, size_label: str) -> str:
    base = settings.API_BASE_URL.rstrip("/")
    return f"{base}/uploads/thumbnails/{blob_hash}?size={size_label}"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _strip_exif(image: Image.Image) -> Image.Image:
    """Return a copy of *image* with all EXIF / metadata removed."""
    clean = Image.new(image.mode, image.size)
    clean.putdata(list(image.getdata()))
    return clean


def _make_generic_thumbnail(label: str, size: int) -> Image.Image:
    """Render a simple coloured tile with the file extension label."""
    dim = (size, size)
    img = Image.new("RGB", dim, color=(45, 55, 72))
    draw = ImageDraw.Draw(img)
    text = label.upper()[:6]
    try:
        font = ImageFont.truetype("arial.ttf", size=max(16, size // 6))
    except (OSError, IOError):
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - tw) / 2, (size - th) / 2), text, fill=(160, 174, 192), font=font)
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
    try:
        import zipfile
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = sorted(n for n in z.namelist() if n.startswith("word/media/") and not n.endswith("/"))
            if not names:
                return None
            with z.open(names[0]) as fh:
                return Image.open(io.BytesIO(fh.read())).copy()
    except Exception as exc:
        logger.warning("DOCX image extraction failed: %s", exc)
        return None


def _get_source_image(data: bytes, mime_type: str, extension: str) -> Image.Image:
    if any(mime_type.startswith(p) for p in IMAGE_MIME_PREFIXES):
        try:
            img = Image.open(io.BytesIO(data)).convert("RGB")
            return _strip_exif(img)
        except UnidentifiedImageError:
            pass

    if mime_type == PDF_MIME:
        img = _source_image_from_pdf(data)
        if img:
            return _strip_exif(img.convert("RGB"))

    if mime_type == DOCX_MIME:
        img = _source_image_from_docx(data)
        if img:
            return _strip_exif(img.convert("RGB"))

    return _make_generic_thumbnail(extension, 1024)


def _generate_webp_thumbnail(source: Image.Image, max_dim: int) -> Tuple[bytes, str]:
    """
    Resize *source* to fit within *max_dim* × *max_dim*, strip any residual
    metadata, and encode as WebP. Returns (webp_bytes, sha256_hex).
    """
    thumb = source.copy()
    thumb.thumbnail((max_dim, max_dim), Image.LANCZOS)
    # Strip again in case Pillow re-attached palette/info during resize.
    clean = _strip_exif(thumb)
    buf = io.BytesIO()
    clean.save(buf, format="WEBP", quality=85, method=4)
    raw = buf.getvalue()
    return raw, hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def generate_and_save_thumbnails(
    blob_hash: str,
    data: bytes,
    mime_type: str,
    extension: str,
) -> dict[str, str]:
    """
    Generate thumbnails for all three sizes, persist them to disk, and
    return a mapping of size_label → public URL.

    This is intentionally self-contained — the worker only needs to call
    this one function and then broadcast the result.
    """
    loop = asyncio.get_event_loop()

    def _blocking() -> dict[str, Tuple[bytes, str]]:
        source = _get_source_image(data, mime_type, extension)
        return {
            label: _generate_webp_thumbnail(source, dim)
            for label, dim in THUMBNAIL_SIZES.items()
        }

    results: dict[str, Tuple[bytes, str]] = await loop.run_in_executor(None, _blocking)

    urls: dict[str, str] = {}
    for label, (thumb_bytes, _digest) in results.items():
        abs_path = thumbnail_abs_path(blob_hash, label)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "wb") as fh:
            fh.write(thumb_bytes)
        urls[label] = thumbnail_url(blob_hash, label)
        logger.debug("Thumbnail saved: %s (%d bytes)", abs_path, len(thumb_bytes))

    return urls
