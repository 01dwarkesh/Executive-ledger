import os
import uuid
from fastapi import UploadFile, HTTPException
from app.config import get_settings

settings = get_settings()

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/svg+xml", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


async def save_upload(file: UploadFile, subdir: str) -> str:
    """
    Validates and saves an uploaded file to UPLOAD_DIR/subdir/.
    Returns the public URL path (/static/subdir/filename.ext).
    Raises 400 on invalid type or size.
    """
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{file.content_type}' not allowed. Use PNG, JPG, SVG, or WebP.",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 5 MB limit.")

    ext = (file.filename or "upload").rsplit(".", 1)[-1].lower()
    filename = f"{uuid.uuid4()}.{ext}"

    dir_path = os.path.join(settings.upload_dir, subdir)
    os.makedirs(dir_path, exist_ok=True)

    with open(os.path.join(dir_path, filename), "wb") as f:
        f.write(contents)

    return f"/static/{subdir}/{filename}"


def delete_file(url_path: str) -> None:
    """Best-effort delete of a previously saved static file."""
    if not url_path or not url_path.startswith("/static/"):
        return
    rel = url_path.replace("/static/", "", 1)
    full = os.path.join(settings.upload_dir, rel)
    try:
        if os.path.exists(full):
            os.remove(full)
    except OSError:
        pass