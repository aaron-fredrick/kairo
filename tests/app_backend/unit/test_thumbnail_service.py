"""Thumbnail generation and persistence."""
import io

import pytest
from PIL import Image

from app_backend.services.thumbnail_service import (
    THUMBNAIL_SIZES,
    _generate_webp_thumbnail,
    _get_source_image,
    _make_generic_thumbnail,
    generate_and_save_thumbnails,
    thumbnail_url,
)
from app_backend.storage.provider import LocalStorageProvider


@pytest.fixture
def storage_provider(tmp_path, monkeypatch):
    import app_backend.storage.provider as provider_mod

    prov = LocalStorageProvider(str(tmp_path))
    monkeypatch.setattr(provider_mod, "_provider", prov)
    return prov


def _tiny_png() -> bytes:
    img = Image.new("RGB", (32, 32), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_thumbnail_url():
    h = "a" * 64
    assert thumbnail_url(h, "128") == f"/api/data/thumbnails?hash={h}&size=128"


def test_generic_thumbnail_and_webp():
    tile = _make_generic_thumbnail("pdf", 128)
    assert tile.size == (128, 128)
    webp, digest = _generate_webp_thumbnail(tile, 128)
    assert len(digest) == 64
    assert webp[:4] == b"RIFF"


def test_get_source_image_from_png():
    source = _get_source_image(_tiny_png(), "image/png", "png")
    assert source.size[0] > 0


@pytest.mark.asyncio
async def test_generate_and_save_thumbnails(storage_provider):
    data = _tiny_png()
    digest = "c" * 64
    urls = await generate_and_save_thumbnails(digest, data, "image/png", "png")
    assert set(urls.keys()) == set(THUMBNAIL_SIZES.keys())
    for label in THUMBNAIL_SIZES:
        rel = f"thumbnails/sha256/{digest[:2]}/{digest[2:4]}/{digest}_{label}.webp"
        assert await storage_provider.exists_path(rel)
