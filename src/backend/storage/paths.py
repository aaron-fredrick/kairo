"""Provider-relative paths (POSIX forward slashes) for all stored artifacts."""


def normalize_posix_path(rel_path: str) -> str:
    return rel_path.replace("\\", "/").lstrip("/")


def temp_upload_path(upload_id: str) -> str:
    return f"temp/uploads/{upload_id}"


def temp_pfp_path(upload_id: str) -> str:
    return f"temp/pfps/{upload_id}"


def thumbnail_path(blob_hash: str, size_label: str) -> str:
    return (
        f"thumbnails/sha256/{blob_hash[:2]}/{blob_hash[2:4]}/"
        f"{blob_hash}_{size_label}.webp"
    )


def pfp_path(pfp_hash: str, size_label: str) -> str:
    return f"pfps/{pfp_hash}_{size_label}.webp"
