"""
文件上传服务

职责：
    - 接收上传的 CSV/JSON 文件并解析为记录列表
    - 调用数据校验器，返回校验报告
    - 管理上传会话（临时存储）
"""

import csv
import io
import json
import os
import time
import uuid
from typing import Any

from app.core.logger import get_logger
from app.core.settings import settings
from app.pipeline.data_validator import DataValidator, ValidationReport

logger = get_logger(__name__)

# 内存缓存：upload_id -> {"records": [...], "created_at": float, ...}
_upload_cache: dict[str, dict[str, Any]] = {}
_CACHE_TTL_SECONDS = 3600  # 1 小时有效期


class UploadService:
    """
    文件上传与解析服务。
    """

    def __init__(self) -> None:
        self._validator = DataValidator()
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    def parse_and_validate(
        self,
        filename: str,
        content: bytes,
    ) -> tuple[str, int, ValidationReport, list[dict[str, Any]]]:
        """
        解析上传文件并进行数据校验。

        Args:
            filename: 原始文件名。
            content: 文件字节内容。

        Returns:
            (upload_id, row_count, validation_report, records) 元组。
        """
        ext = os.path.splitext(filename)[1].lower()

        if ext == ".json":
            records = self._parse_json(content)
        elif ext == ".csv":
            records = self._parse_csv(content)
        else:
            raise ValueError(f"不支持的文件格式: {ext}，仅支持 .csv / .json")

        validation_report = self._validator.validate_oil_data(records)

        if validation_report.passed:
            filled, repair_log = self._validator.fill_missing_values_with_log(records)
            validation_report.repair_log = repair_log
            records = filled

        upload_id = str(uuid.uuid4())
        _upload_cache[upload_id] = {
            "records": records,
            "filename": filename,
            "created_at": time.time(),
            "row_count": len(records),
        }
        self._evict_expired()

        logger.info(f"UploadService: 上传完成 upload_id={upload_id} rows={len(records)}")
        return upload_id, len(records), validation_report, records

    def get_records(self, upload_id: str) -> list[dict[str, Any]] | None:
        """
        通过 upload_id 取回上传记录。

        Args:
            upload_id: 上传 ID。

        Returns:
            记录列表，未找到或已过期时返回 None。
        """
        entry = _upload_cache.get(upload_id)
        if not entry:
            return None
        if time.time() - entry["created_at"] > _CACHE_TTL_SECONDS:
            del _upload_cache[upload_id]
            return None
        return entry["records"]

    def get_status(self, upload_id: str) -> dict[str, Any] | None:
        """获取上传状态信息。"""
        entry = _upload_cache.get(upload_id)
        if not entry:
            return None
        age = time.time() - entry["created_at"]
        if age > _CACHE_TTL_SECONDS:
            del _upload_cache[upload_id]
            return None
        from datetime import datetime, timezone
        return {
            "upload_id": upload_id,
            "status": "ready",
            "row_count": entry["row_count"],
            "created_at": datetime.fromtimestamp(
                entry["created_at"], tz=timezone.utc
            ).isoformat(),
        }

    def _parse_json(self, content: bytes) -> list[dict[str, Any]]:
        data = json.loads(content.decode("utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        raise ValueError("JSON 文件格式无法识别，期望为列表或包含 'data' 键的字典")

    def _parse_csv(self, content: bytes) -> list[dict[str, Any]]:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        records: list[dict[str, Any]] = []
        for row in reader:
            parsed_row: dict[str, Any] = {}
            for k, v in row.items():
                key = k.strip().lower()
                try:
                    parsed_row[key] = float(v) if key != "date" else v.strip()
                except (ValueError, TypeError):
                    parsed_row[key] = v.strip() if v else None
            records.append(parsed_row)
        return records

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [uid for uid, e in _upload_cache.items() if now - e["created_at"] > _CACHE_TTL_SECONDS]
        for uid in expired:
            del _upload_cache[uid]
