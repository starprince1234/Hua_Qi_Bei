"""统计筛选理由服务。"""

from __future__ import annotations

import json
from pathlib import Path
from collections import Counter


class FactorReasonService:
    def __init__(self, data_path: str | None = None) -> None:
        default_path = Path(__file__).resolve().parents[2] / "data" / "selected_factor_reasons.json"
        self._path = Path(data_path) if data_path else default_path

    def get_all_reasons(self) -> dict:
        if not self._path.exists():
            return {"selected": [], "dropped": []}
        with self._path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def build_summary(self, top_factor_names: list[str]) -> dict:
        payload = self.get_all_reasons()
        selected = payload.get("selected", [])
        dropped = payload.get("dropped", [])

        selected_map = {item.get("factor_name"): item for item in selected}
        selected_hits = [selected_map[name] for name in top_factor_names if name in selected_map]

        tag_counter: Counter[str] = Counter()
        for item in selected_hits:
            for tag in item.get("reason_tags", []):
                tag_counter[tag] += 1

        return {
            "selected_count": len(selected),
            "dropped_count": len(dropped),
            "matched_top_factors": [item.get("factor_name") for item in selected_hits],
            "top_reason_tags": [
                {"tag": tag, "count": count}
                for tag, count in tag_counter.most_common(5)
            ],
        }

    def get_reason_catalog(self) -> dict:
        payload = self.get_all_reasons()
        tag_set: set[str] = set()
        for key in ("selected", "dropped"):
            for item in payload.get(key, []):
                for tag in item.get("reason_tags", []):
                    tag_set.add(tag)

        reason_tags = [
            {
                "reason_tag": tag,
                "name_cn": tag,
                "description": f"{tag} 规则命中",
                "severity": "info",
            }
            for tag in sorted(tag_set)
        ]
        return {"total": len(reason_tags), "reason_tags": reason_tags}

    def build_factor_selection_reasons(self, top_factor_names: list[str]) -> dict:
        payload = self.get_all_reasons()

        selected_items = []
        for item in payload.get("selected", []):
            factor = item.get("factor_name", "")
            for tag in item.get("reason_tags", [])[:1]:
                selected_items.append(
                    {
                        "factor": factor,
                        "reason_tag": tag,
                        "evidence": {
                            "matched_top_factor": factor in top_factor_names,
                        },
                    }
                )

        rejected_items = []
        for item in payload.get("dropped", []):
            factor = item.get("factor_name", "")
            for tag in item.get("reason_tags", [])[:1]:
                rejected_items.append(
                    {
                        "factor": factor,
                        "reason_tag": tag,
                        "evidence": {
                            "matched_top_factor": factor in top_factor_names,
                        },
                    }
                )

        return {"selected": selected_items, "rejected": rejected_items}
