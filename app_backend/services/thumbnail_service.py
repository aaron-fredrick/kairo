"""
Thumbnail generation service.

Output path (provider-relative): thumbnails/sha256/<2>/<2>/<blob_hash>_<size>.webp
"""
from __future__ import annotations

import asyncio
import hashlib
import io
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError

from app_backend.core.logging import get_logger
from app_backend.storage.paths import thumbnail_path
from app_backend.storage.provider import get_storage_provider

logger = get_logger(__name__)

THUMBNAIL_SIZES: dict[str, int] = {
    "128": 128,
    "512": 512,
    "1024": 1024,
}

IMAGE_MIME_PREFIXES = ("image/",)
PDF_MIME = "application/pdf"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def thumbnail_url(blob_hash: str, size_label: str) -> str:
    return f"/api/data/thumbnails?hash={blob_hash}&size={size_label}"


def _strip_exif(image: Image.Image) -> Image.Image:
    clean = Image.new(image.mode, image.size)
    clean.putdata(list(image.getdata()))
    return clean


def _make_generic_thumbnail(label: str, size: int) -> Image.Image:
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
    thumb = source.copy()
    thumb.thumbnail((max_dim, max_dim), Image.LANCZOS)
    clean = _strip_exif(thumb)
    buf = io.BytesIO()
    clean.save(buf, format="WEBP", quality=85, method=4)
    raw = buf.getvalue()
    return raw, hashlib.sha256(raw).hexdigest()


async def generate_and_save_thumbnails(
    blob_hash: str,
    data: bytes,
    mime_type: str,
    extension: str,
) -> dict[str, str]:
    loop = asyncio.get_event_loop()

    def _blocking() -> dict[str, Tuple[bytes, str]]:
        source = _get_source_image(data, mime_type, extension)
        return {
            label: _generate_webp_thumbnail(source, dim)
            for label, dim in THUMBNAIL_SIZES.items()
        }

    results: dict[str, Tuple[bytes, str]] = await loop.run_in_executor(None, _blocking)
    provider = get_storage_provider()

    urls: dict[str, str] = {}
    for label, (thumb_bytes, _digest) in results.items():
        rel = thumbnail_path(blob_hash, label)
        await provider.put_path(rel, thumb_bytes)
        urls[label] = thumbnail_url(blob_hash, label)
        logger.debug("Thumbnail saved: %s (%d bytes)", rel, len(thumb_bytes))

    return urls
