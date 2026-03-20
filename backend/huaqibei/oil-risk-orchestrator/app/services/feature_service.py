from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.core.settings import get_settings
from app.core.errors import NotFoundError, ValidationError
from app.core.logger import get_logger
from app.pipeline.data_validator import validate_dataframe
from app.pipeline.lag_builder import build_lags
from app.pipeline.interaction_builder import build_interactions
from app.pipeline.asof_aligner import align_series

logger = get_logger(__name__)


async def load_and_preprocess(file_id: str) -> pd.DataFrame:
    """Load uploaded file and return a feature-engineered DataFrame ready for the model."""
    settings = get_settings()
    upload_dir = Path(settings.UPLOAD_DIR)

    # file_id already contains the extension suffix from upload_service
    path = upload_dir / file_id
    if not path.exists():
        # Try without extension (legacy)
        candidates = list(upload_dir.glob(f"{file_id}*"))
        if not candidates:
            raise NotFoundError(f"Uploaded file not found: {file_id}")
        path = candidates[0]

    ext = path.suffix.lower()
    if ext == ".csv":
        df = pd.read_csv(path, parse_dates=True, index_col=0)
    elif ext == ".parquet":
        df = pd.read_parquet(path)
    else:
        df = pd.read_excel(path, index_col=0, parse_dates=True)

    logger.info("File loaded", extra={"file_id": file_id, "shape": str(df.shape)})

    result = validate_dataframe(df)
    if result.errors:
        raise ValidationError("Data validation failed", {"errors": result.errors})

    # Align index
    df = align_series(df)

    # Lag features
    numeric_cols = df.select_dtypes("number").columns.tolist()
    df = build_lags(df, numeric_cols)

    # Interaction features
    df = build_interactions(df, numeric_cols[:6])  # limit combinations

    df = df.dropna()
    logger.info("Preprocessing complete", extra={"file_id": file_id, "final_shape": str(df.shape)})
    return df
