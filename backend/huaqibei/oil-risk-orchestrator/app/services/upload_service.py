from __future__ import annotations

import os
import uuid
from pathlib import Path

import pandas as pd

from app.core.settings import get_settings
from app.core.errors import UploadError
from app.core.logger import get_logger
from app.schemas.upload_schema import UploadData

logger = get_logger(__name__)


def get_upload_path(file_id: str) -> Path:
    settings = get_settings()
    return Path(settings.UPLOAD_DIR) / file_id


async def save_upload(file) -> UploadData:  # type: ignore[type-arg]
    settings = get_settings()
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = file.filename or "upload"
    ext = Path(filename).suffix.lower()
    if ext not in {".csv", ".parquet", ".xls", ".xlsx"}:
        raise UploadError(f"Unsupported file type: {ext}. Allowed: .csv, .parquet, .xls, .xlsx")

    file_id = str(uuid.uuid4())
    dest = upload_dir / f"{file_id}{ext}"

    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise UploadError(f"File exceeds maximum size of {settings.MAX_UPLOAD_MB} MB")

    dest.write_bytes(content)
    logger.info("File saved", extra={"file_id": file_id, "path": str(dest), "bytes": len(content)})

    # Generate preview
    try:
        if ext == ".csv":
            df = pd.read_csv(dest, nrows=5)
        elif ext == ".parquet":
            df = pd.read_parquet(dest).head(5)
        else:
            df = pd.read_excel(dest, nrows=5)
        preview = df.fillna("").astype(str).to_dict(orient="records")
    except Exception:
        preview = []

    return UploadData(
        file_id=file_id + ext,
        filename=filename,
        size=len(content),
        preview=preview,
    )
