from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd


FACTOR_CATEGORIES = ["inventory", "geo", "macro", "supply_demand", "technical"]
KEY_EVENT_LABELS = {
    "2020-04-20": "负油价冲击",
    "2022-02-24": "俄乌战争爆发",
    "2022-03-08": "俄油制裁冲击",
    "2023-10-07": "巴以冲突爆发",
    "2024-04-13": "中东冲突升级",
}


@dataclass(frozen=True)
class BuildConfig:
    source_file: Path
    output_dir: Path
    target: str
    horizon: int
    test_start: str
    max_points: int


def parse_args() -> BuildConfig:
    parser = argparse.ArgumentParser(
        description="Build real validation JSON from Hua Qi Bei raw Excel data."
    )
    parser.add_argument("--source-file", required=True, help="Excel file with feature and return columns.")
    parser.add_argument("--output-dir", required=True, help="Directory for generated JSON files.")
    parser.add_argument("--target", default="Brent", help="Target name for generated payloads.")
    parser.add_argument("--horizon", type=int, default=7, help="Return horizon in days.")
    parser.add_argument(
        "--test-start",
        default="2022-01-01",
        help="First date used for out-of-sample validation.",
    )
    parser.add_argument(
        "--max-points",
        type=int,
        default=260,
        help="Maximum number of displayed validation points.",
    )
    args = parser.parse_args()
    return BuildConfig(
        source_file=Path(args.source_file),
        output_dir=Path(args.output_dir),
        target=str(args.target),
        horizon=int(args.horizon),
        test_start=str(args.test_start),
        max_points=int(args.max_points),
    )


def main() -> int:
    config = parse_args()
    frame = _load_source(config)
    validation = _build_validation_frame(frame, config)
    metadata = _build_metadata(validation, config)
    backtest = _build_backtest_payload(validation, config, metadata)
    factor_history = _build_factor_history_payload(validation, config, metadata)

    config.output_dir.mkdir(parents=True, exist_ok=True)
    backtest_path = config.output_dir / f"backtest_{config.target}_{config.horizon}d.json"
    factor_path = config.output_dir / f"factor_history_{config.target}_{config.horizon}d.json"
    backtest_path.write_text(json.dumps(backtest, ensure_ascii=False, indent=2), encoding="utf-8")
    factor_path.write_text(json.dumps(factor_history, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "backtest": str(backtest_path),
                "factor_history": str(factor_path),
                "rows": len(validation),
                "window": backtest["window"],
                "metrics": backtest["metrics"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _load_source(config: BuildConfig) -> pd.DataFrame:
    frame = pd.read_excel(config.source_file)
    date_column = "日期"
    target_column = f"{config.target}_{config.horizon}日涨跌幅(%)"
    if target_column not in frame.columns:
        raise ValueError(f"Missing target column: {target_column}")
    if date_column not in frame.columns:
        raise ValueError(f"Missing date column: {date_column}")

    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame[date_column], errors="coerce")
    frame["actual_return"] = pd.to_numeric(frame[target_column], errors="coerce") / 100.0
    frame["actual_price"] = pd.to_numeric(frame["Brent_Crude(BZ=F)_Close"], errors="coerce")
    frame = frame.dropna(subset=["date", "actual_return", "actual_price"]).sort_values("date")
    return frame.reset_index(drop=True)


def _build_validation_frame(frame: pd.DataFrame, config: BuildConfig) -> pd.DataFrame:
    feature_columns = _feature_columns(frame)
    train_mask = frame["date"] < pd.Timestamp(config.test_start)
    train = frame.loc[train_mask].copy()
    if train.empty:
        raise ValueError("Train/test split produced an empty partition.")

    means = train[feature_columns].apply(pd.to_numeric, errors="coerce").mean()
    stds = train[feature_columns].apply(pd.to_numeric, errors="coerce").std().replace(0, 1.0)
    x_train = ((train[feature_columns].apply(pd.to_numeric, errors="coerce") - means) / stds).fillna(0.0)
    x_all = ((frame[feature_columns].apply(pd.to_numeric, errors="coerce") - means) / stds).fillna(0.0)
    y_train = train["actual_return"].astype(float)
    coefficients, intercept = _fit_ridge(x_train, y_train, alpha=5.0)

    predicted = intercept + x_all.to_numpy().dot(coefficients)
    residual_std = float((y_train - (intercept + x_train.to_numpy().dot(coefficients))).std())
    if not math.isfinite(residual_std) or residual_std <= 0:
        residual_std = float(y_train.std() or 0.01)

    result = frame.copy()
    result["predicted_return"] = predicted
    result["lower_return"] = result["predicted_return"] - 1.64 * residual_std
    result["upper_return"] = result["predicted_return"] + 1.64 * residual_std
    result["predicted_price"] = result["actual_price"] / (1.0 + result["actual_return"]) * (
        1.0 + result["predicted_return"]
    )
    result["lower_price"] = result["actual_price"] / (1.0 + result["actual_return"]) * (
        1.0 + result["lower_return"]
    )
    result["upper_price"] = result["actual_price"] / (1.0 + result["actual_return"]) * (
        1.0 + result["upper_return"]
    )
    result["hit_interval"] = (
        (result["actual_return"] >= result["lower_return"])
        & (result["actual_return"] <= result["upper_return"])
    )

    contribution_frame = _factor_contributions(x_all, coefficients, feature_columns)
    for category in FACTOR_CATEGORIES:
        result[category] = contribution_frame[category].to_numpy()
    result["event_label"] = result.apply(_event_label, axis=1)
    return result.reset_index(drop=True)


def _feature_columns(frame: pd.DataFrame) -> list[str]:
    excluded = {"日期", "date", "actual_return"}
    candidates: list[str] = []
    for column in frame.columns:
        if column in excluded or str(column).startswith("Brent_7日涨跌幅"):
            continue
        series = pd.to_numeric(frame[column], errors="coerce")
        if series.notna().sum() >= 100:
            candidates.append(str(column))
    return candidates


def _fit_ridge(x: pd.DataFrame, y: pd.Series, *, alpha: float) -> tuple[Any, float]:
    import numpy as np

    x_values = x.to_numpy(dtype=float)
    y_values = y.to_numpy(dtype=float)
    x_augmented = np.column_stack([np.ones(len(x_values)), x_values])
    identity = np.eye(x_augmented.shape[1])
    identity[0, 0] = 0.0
    beta = np.linalg.solve(x_augmented.T @ x_augmented + alpha * identity, x_augmented.T @ y_values)
    return beta[1:], float(beta[0])


def _factor_contributions(
    x_test: pd.DataFrame,
    coefficients: Any,
    feature_columns: list[str],
) -> pd.DataFrame:
    import numpy as np

    raw = np.abs(x_test.to_numpy(dtype=float) * coefficients)
    buckets = {category: np.zeros(len(x_test)) for category in FACTOR_CATEGORIES}
    for index, column in enumerate(feature_columns):
        buckets[_category_for_column(column)] += raw[:, index]
    total = sum(buckets.values())
    total = np.where(total <= 0, 1.0, total)
    return pd.DataFrame({category: buckets[category] / total for category in FACTOR_CATEGORIES})


def _category_for_column(column: str) -> str:
    text = column.lower()
    if any(token in column for token in ["库存", "SPR", "战略储备", "释放"]):
        return "inventory"
    if any(token in text for token in ["opec", "sanction", "geo"]):
        return "geo"
    if any(token in column for token in ["制裁", "地缘", "衰减", "OPEC"]):
        return "geo"
    if any(token in text for token in ["dxy", "t5yie", "rate", "inflation"]):
        return "macro"
    if any(token in text for token in ["gasoline", "crack", "wti", "volume", "spread"]):
        return "supply_demand"
    if any(token in column for token in ["天气", "飓风"]):
        return "supply_demand"
    return "technical"


def _event_label(row: pd.Series) -> str | None:
    date_value = row.get("date")
    if hasattr(date_value, "date"):
        key_label = KEY_EVENT_LABELS.get(date_value.date().isoformat())
        if key_label:
            return key_label

    checks = [
        ("战略储备释放", "战略储备释放_量化值", 0.0),
        ("OPEC+ 决议", "OPEC+会议量化值", 0.0),
        ("极端天气/飓风", "极端天气_量化值", 3.0),
        ("地缘政治事件", "地缘政治事件_量化值", 2.0),
        ("制裁/解禁事件", "制裁&解禁_量化值", 3.0),
    ]
    for label, column, threshold in checks:
        value = row.get(column)
        try:
            if abs(float(value)) > threshold:
                return label
        except (TypeError, ValueError):
            continue
    return None


def _build_metadata(validation: pd.DataFrame, config: BuildConfig) -> dict[str, str]:
    window = f"{validation['date'].min().date().isoformat()}/{validation['date'].max().date().isoformat()}"
    model_version = "ridge_baseline_from_raw_v1"
    identity = "|".join([config.target, str(config.horizon), config.test_start, window, model_version])
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    return {
        "run_id": f"offline_validation_{digest}",
        "model_version": model_version,
        "updated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "window": window,
    }


def _build_backtest_payload(
    validation: pd.DataFrame,
    config: BuildConfig,
    metadata: dict[str, str],
) -> dict[str, Any]:
    display = _sample_points(validation, config.max_points)
    errors = validation["predicted_return"] - validation["actual_return"]
    actual_price = validation["actual_price"].astype(float)
    predicted_price = validation["predicted_price"].astype(float)
    metrics = {
        "direction_accuracy": _round(((validation["predicted_return"] >= 0) == (validation["actual_return"] >= 0)).mean()),
        "rmse": _round(math.sqrt(float(((predicted_price - actual_price) ** 2).mean()))),
        "mape": _round((abs(predicted_price - actual_price) / actual_price.replace(0, math.nan)).mean()),
        "interval_hit_rate": {
            "all": _round(validation["hit_interval"].mean()),
            "low": _hit_rate_by_abs_return(validation, 0.0, 0.02),
            "medium": _hit_rate_by_abs_return(validation, 0.02, 0.05),
            "high": _hit_rate_by_abs_return(validation, 0.05, float("inf")),
        },
    }
    return {
        "target": config.target,
        "window": metadata["window"],
        "metrics": metrics,
        "stage_metrics": _stage_metrics(validation),
        "provider_status": "offline_validation",
        "run_id": metadata["run_id"],
        "model_version": metadata["model_version"],
        "updated_at": metadata["updated_at"],
        "points": [
            {
                "date": row.date.date().isoformat(),
                "actual_price": _round(row.actual_price),
                "predicted_price": _round(row.predicted_price),
                "lower_price": _round(row.lower_price),
                "upper_price": _round(row.upper_price),
            }
            for row in display.itertuples()
        ],
        "events": _event_marks(validation),
        "bins": _error_bins(errors),
    }


def _build_factor_history_payload(
    validation: pd.DataFrame,
    config: BuildConfig,
    metadata: dict[str, str],
) -> dict[str, Any]:
    display = _sample_points(validation, config.max_points)
    return {
        "categories": FACTOR_CATEGORIES,
        "provider_status": "offline_validation",
        "run_id": metadata["run_id"],
        "updated_at": metadata["updated_at"],
        "points": [
            {
                "date": row.date.date().isoformat(),
                "inventory": _round(row.inventory),
                "geo": _round(row.geo),
                "macro": _round(row.macro),
                "supply_demand": _round(row.supply_demand),
                "technical": _round(row.technical),
                "event_label": row.event_label if isinstance(row.event_label, str) else None,
                f"predicted_return_{config.horizon}d": _round(row.predicted_return),
                f"lower_return_{config.horizon}d": _round(row.lower_return),
                f"upper_return_{config.horizon}d": _round(row.upper_return),
                f"actual_return_{config.horizon}d": _round(row.actual_return),
                "predicted_return_7d": _round(row.predicted_return),
                "lower_return_7d": _round(row.lower_return),
                "upper_return_7d": _round(row.upper_return),
                "actual_return_7d": _round(row.actual_return),
                "hit_interval": bool(row.hit_interval),
            }
            for row in display.itertuples()
        ],
    }


def _sample_points(frame: pd.DataFrame, max_points: int) -> pd.DataFrame:
    if len(frame) <= max_points:
        return frame
    step = max(1, len(frame) // max_points)
    sampled = frame.iloc[::step].copy()
    return sampled.tail(max_points)


def _hit_rate_by_abs_return(frame: pd.DataFrame, lower: float, upper: float) -> float:
    absolute = frame["actual_return"].abs()
    mask = (absolute >= lower) & (absolute < upper)
    if not mask.any():
        return 0.0
    return _round(frame.loc[mask, "hit_interval"].mean())


def _stage_metrics(frame: pd.DataFrame) -> list[dict[str, Any]]:
    stages = [
        ("平稳期（2015-2019）", "2015-01-01", "2019-12-31"),
        ("高波动期（2020-2022）", "2020-01-01", "2022-12-31"),
        ("恢复期（2023-2025）", "2023-01-01", "2025-12-31"),
    ]
    rows: list[dict[str, Any]] = []
    for label, start, end in stages:
        subset = frame[(frame["date"] >= pd.Timestamp(start)) & (frame["date"] <= pd.Timestamp(end))]
        if subset.empty:
            continue
        rmse = math.sqrt(float(((subset["predicted_price"] - subset["actual_price"]) ** 2).mean()))
        rows.append(
            {
                "stage": label,
                "direction_accuracy": _round(((subset["predicted_return"] >= 0) == (subset["actual_return"] >= 0)).mean()),
                "rmse": _round(rmse),
            }
        )
    return rows


def _event_marks(frame: pd.DataFrame) -> list[dict[str, Any]]:
    labeled = frame[frame["event_label"].notna()].copy()
    key_events = labeled[labeled["date"].dt.date.astype(str).isin(KEY_EVENT_LABELS)].copy()
    high_move_events = frame.reindex(frame["actual_return"].abs().sort_values(ascending=False).head(12).index).copy()
    high_move_events["event_label"] = high_move_events["event_label"].fillna("高波动验证点")
    remaining = labeled.sort_values("date").tail(12)
    events = pd.concat([key_events, high_move_events, remaining]).drop_duplicates(subset=["date"]).sort_values("date")
    if events.empty:
        events = high_move_events.sort_values("date")
    if len(events) > 20:
        key_dates = set(KEY_EVENT_LABELS)
        key_rows = events[events["date"].dt.date.astype(str).isin(key_dates)]
        other_rows = events[~events["date"].dt.date.astype(str).isin(key_dates)].copy()
        other_rows["_event_rank"] = other_rows["actual_return"].abs()
        other_rows = other_rows.sort_values("_event_rank", ascending=False).head(max(0, 20 - len(key_rows)))
        events = pd.concat([key_rows, other_rows]).drop(columns=["_event_rank"], errors="ignore").sort_values("date")
    return [
        {
            "date": row.date.date().isoformat(),
            "label": str(row.event_label),
            "hit_interval": bool(row.hit_interval),
            "actual_return_7d": _round(row.actual_return),
            "predicted_return_7d": _round(row.predicted_return),
        }
        for row in events.sort_values("date").itertuples()
    ]


def _error_bins(errors: pd.Series) -> list[dict[str, Any]]:
    percent_errors = errors.astype(float) * 100
    bins = [(-10, -7), (-7, -5), (-5, -3), (-3, -1), (-1, 1), (1, 3), (3, 5), (5, 7), (7, 10)]
    rows = []
    for lower, upper in bins:
        count = int(((percent_errors >= lower) & (percent_errors < upper)).sum())
        rows.append({"range": f"{lower}~{upper}", "count": count})
    return rows


def _round(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(number):
        return 0.0
    return round(number, 6)


if __name__ == "__main__":
    raise SystemExit(main())
