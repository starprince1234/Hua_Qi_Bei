"""
远程模型调用客户端

职责：
    - ⭐ 封装对云端模型 API 的所有调用
    - 处理超时、重试、错误格式化
    - 返回标准化的 ModelRawResponse

禁止：
    - 在此文件中做特征工程
    - 在此文件中做业务逻辑
    - 在路由层直接调用 HTTPX
"""

import asyncio
import json
import math
import httpx
from typing import Optional, Any
from urllib.parse import urlparse, urlunparse

from app.schemas.model_response_schema import (
    ModelRawResponse,
    ShapValues,
    MultiHorizonReturnPoint,
)
from app.core.settings import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

VOLATILITY_FEATURE_MAP: dict[str, list[str]] = {
    "1日波动率": [
        "Brent_Crude(BZ=F)_Close",
        "OVX_日涨跌幅 (%)",
        "Gasoline_7日涨跌幅(%)",
        "T5YIE_趋势标记(1=上升,0=下降)",
    ],
    "3日波动率": [
        "Gasoline_7日涨跌幅(%)",
        "Brent_close_1日差分",
        "OVX_日涨跌幅 (%)",
        "T5YIE_趋势标记(1=上升,0=下降)",
        "T5YIE_30日差分",
        "Crack_Spread_3日差分",
    ],
    "7日波动率": [
        "Gasoline_7日涨跌幅(%)",
        "Brent_close_1日差分",
        "T5YIE_趋势标记(1=上升,0=下降)",
        "T5YIE_30日差分",
        "OVX_3日滚动标准差",
        "OVX_日涨跌幅 (%)",
        "Brent_当日波动幅度(%)",
        "OVX",
        "T5YIE_30日涨跌幅(%)",
        "Crack_Spread_趋势标记(1=上升,0=下降)",
        "衰减系数",
    ],
    "14日波动率": [
        "Gasoline_7日涨跌幅(%)",
        "T5YIE_30日差分",
        "T5YIE_趋势标记(1=上升,0=下降)",
        "T5YIE_30日涨跌幅(%)",
        "OVX_3日滚动标准差",
        "Brent_close_1日差分",
        "OVX",
        "Brent_当日波动幅度(%)",
        "OVX_滞后1日",
        "DXY",
        "DXY_滞后1日",
        "DXY_7日滚动均值",
        "OVX_滞后3日",
        "Brent_close_7日滚动标准差",
        "DXY_滞后7日",
        "OVX_日涨跌幅 (%)",
    ],
    "30日波动率": [
        "T5YIE_30日差分",
        "T5YIE_30日涨跌幅(%)",
        "T5YIE_趋势标记(1=上升,0=下降)",
        "Gasoline_7日涨跌幅(%)",
        "OVX",
        "OVX_滞后1日",
        "Brent_当日波动幅度(%)",
        "OVX_滞后3日",
        "DXY",
        "DXY_滞后1日",
        "DXY_7日滚动均值",
        "OVX_3日滚动标准差",
        "DXY_滞后7日",
        "Brent_close_1日差分",
        "WTI_Crude(CL=F)_Close",
        "Brent_close_7日滚动标准差",
        "Brent_Crude(BZ=F)_Close",
        "T5YIE",
        "Gasoline",
        "Brent_Crude(BZ=F)_Volume",
    ],
}

VOLATILITY_HORIZON_MAP: dict[str, int] = {
    "1日波动率": 1,
    "3日波动率": 3,
    "7日波动率": 7,
    "14日波动率": 14,
    "30日波动率": 30,
}


class ModelClient:
    """
    云端模型 API 客户端。

    支持：
        - POST JSON 调用
        - 自动重试（指数退避）
        - API Key 鉴权
        - 标准化响应解析
    """

    def __init__(
        self,
        model_api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
    ) -> None:
        """
        初始化客户端。

        Args:
            model_api_url: 模型 API 地址，默认读取 settings。
            api_key: Bearer Token，默认读取 settings。
            timeout: 超时秒数，默认读取 settings。
            max_retries: 最大重试次数，默认读取 settings。
        """
        self._url = model_api_url or settings.MODEL_API_URL
        self._api_key = api_key or settings.MODEL_API_KEY
        self._timeout = timeout or settings.MODEL_API_TIMEOUT
        self._max_retries = max_retries or settings.MODEL_API_MAX_RETRIES
        self._model_id = settings.MODEL_API_MODEL_ID
        self._mode = self._detect_mode(self._url)
        self._predict_url = self._build_predict_returns_url(self._url)

    @property
    def mode(self) -> str:
        """返回当前调用模式（openai / legacy）。"""
        return self._mode

    def _detect_mode(self, base_url: str) -> str:
        parsed = urlparse(base_url)
        path = (parsed.path or "").rstrip("/")
        if path.endswith("/chat/completions"):
            return "openai"
        if path.endswith("/v1"):
            return "openai"
        return "legacy"

    def _build_predict_returns_url(self, base_url: str) -> str:
        if self._mode == "openai":
            parsed = urlparse(base_url)
            path = (parsed.path or "").rstrip("/")
            if path.endswith("/chat/completions"):
                final_path = path
            elif path.endswith("/v1"):
                final_path = path + "/chat/completions"
            else:
                final_path = path + "/v1/chat/completions"
            return urlunparse(parsed._replace(path=final_path))

        parsed = urlparse(base_url)
        path = parsed.path or ""

        if path.endswith("/predict/returns"):
            final_path = path
        elif path.endswith("/predict"):
            final_path = path.rstrip("/") + "/returns"
        else:
            final_path = path.rstrip("/") + "/predict/returns"

        return urlunparse(parsed._replace(path=final_path))

    def _build_headers(self) -> dict[str, str]:
        """构建请求头。"""
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def predict(
        self,
        feature_vector: dict,
        forecast_horizon: int = 5,
        include_shap: bool = True,
        current_price: Optional[float] = None,
    ) -> ModelRawResponse:
        """
        调用远程模型获取预测结果。

        Args:
            feature_vector: 标准化特征字典（来自 FeatureService）。
            forecast_horizon: 预测步数。
            include_shap: 是否请求 SHAP 解释。

        Returns:
            ModelRawResponse 标准化响应。

        Raises:
            RuntimeError: 超过最大重试次数后仍失败时抛出。
        """
        payload = {
            "features": feature_vector,
            "forecast_horizon": forecast_horizon,
            "include_shap": include_shap,
        }

        last_exception: Optional[Exception] = None

        for attempt in range(1, self._max_retries + 1):
            try:
                logger.info(
                    f"调用云端模型 attempt={attempt}/{self._max_retries} "
                    f"url={self._predict_url}"
                )
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    if self._mode == "openai":
                        response = await client.post(
                            self._predict_url,
                            json=self._build_openai_payload(
                                feature_vector=feature_vector,
                                forecast_horizon=forecast_horizon,
                                include_shap=include_shap,
                                current_price=current_price,
                            ),
                            headers=self._build_headers(),
                        )
                    else:
                        response = await client.post(
                            self._predict_url,
                            json=payload,
                            headers=self._build_headers(),
                        )
                    response.raise_for_status()
                    raw = response.json()
                    if self._mode == "openai":
                        normalized = self._parse_openai_response(
                            raw,
                            forecast_horizon,
                            current_price=current_price,
                        )
                    else:
                        normalized = raw
                    return self._parse_response(normalized, forecast_horizon)

            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(f"模型调用超时 attempt={attempt}: {e}")
            except httpx.HTTPStatusError as e:
                last_exception = e
                logger.warning(
                    f"模型调用 HTTP 错误 attempt={attempt} "
                    f"status={e.response.status_code}: {e}"
                )
            except Exception as e:
                last_exception = e
                logger.error(f"模型调用未知错误 attempt={attempt}: {e}")

            if attempt < self._max_retries:
                wait_time = 2 ** (attempt - 1)  # 指数退避
                logger.info(f"等待 {wait_time}s 后重试...")
                await asyncio.sleep(wait_time)

        raise RuntimeError(
            f"云端模型调用失败，已重试 {self._max_retries} 次。"
            f"最后错误: {last_exception}"
        )

    def _build_openai_payload(
        self,
        feature_vector: dict,
        forecast_horizon: int,
        include_shap: bool,
        current_price: Optional[float],
    ) -> dict[str, Any]:
        compact_vector = {
            k: float(v)
            for k, v in feature_vector.items()
            if isinstance(v, (int, float))
        }

        filtered_features: dict[str, list[float]] = {}
        for vol_type, cols in VOLATILITY_FEATURE_MAP.items():
            values = []
            for col in cols:
                val = compact_vector.get(col, 0.0)
                values.append(float(val))
            filtered_features[vol_type] = values

        request_body = {
            "task_type": "oil_volatility_prediction",
            "current_price": float(current_price) if current_price is not None else 0.0,
            # 为兼容 test.py 服务保留这些字段
            "filtered_features": filtered_features,
            "volatility_feature_map": VOLATILITY_FEATURE_MAP,
        }

        return {
            "model": self._model_id,
            "messages": [
                {"role": "user", "content": json.dumps(request_body, ensure_ascii=False)}
            ],
            "temperature": 0.0,
        }

    def _parse_openai_response(
        self,
        raw: dict,
        forecast_horizon: int,
        current_price: Optional[float] = None,
    ) -> dict[str, Any]:
        choices = raw.get("choices")
        if not choices:
            raise RuntimeError("OpenAI 响应缺少 choices 字段")

        content = (choices[0].get("message") or {}).get("content")
        if not content:
            raise RuntimeError("OpenAI 响应 message.content 为空")

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"OpenAI 响应内容不是合法 JSON: {e}")

        # 格式1：已是后端期望结构
        if all(k in parsed for k in ("median", "upper", "lower")):
            return parsed

        # 格式2：test.py 风格 volatility_results
        vol_results = parsed.get("volatility_results")
        if isinstance(vol_results, list) and vol_results:
            horizon_map = {v: k for k, v in VOLATILITY_HORIZON_MAP.items()}
            preferred = horizon_map.get(forecast_horizon)
            target = None
            multi_horizon: list[dict[str, float | int]] = []

            ref_price = float(current_price or 0.0)

            def _normalize_predicted_return(raw_pred: float, ref_price: float) -> float:
                # 经验规则：若值落在百分比区间（如 -2.2 表示 -2.2%），按百分比还原。
                if abs(raw_pred) > 1.0:
                    return raw_pred / 100.0
                return raw_pred

            def _normalize_interval_to_returns(
                raw_lower: float,
                raw_upper: float,
                predicted_return: float,
                ref_price: float,
            ) -> tuple[float, float]:
                # 若区间看起来是绝对价格（通常 > 2 且基准价可用），转为对数收益率。
                if ref_price > 0 and raw_lower > 0 and raw_upper > 0 and (raw_lower > 2.0 or raw_upper > 2.0):
                    lower_ret = math.log(raw_lower / ref_price)
                    upper_ret = math.log(raw_upper / ref_price)
                    return (lower_ret, upper_ret)

                # 若区间看起来是百分比（如 -3.5, 2.1），转小数。
                if abs(raw_lower) > 1.0 or abs(raw_upper) > 1.0:
                    return (raw_lower / 100.0, raw_upper / 100.0)

                # 默认认为已是收益率小数。
                return (raw_lower, raw_upper)

            for item in vol_results:
                horizon_name = item.get("volatility_type")
                mapped_horizon = VOLATILITY_HORIZON_MAP.get(str(horizon_name), 0)
                if mapped_horizon <= 0:
                    continue

                pred_i_raw = float(item.get("predicted_return", 0.0))
                pred_i = _normalize_predicted_return(pred_i_raw, ref_price)

                risk_i = item.get("risk_interval") or [pred_i, pred_i]
                raw_lower_i = float(risk_i[0]) if len(risk_i) >= 2 else pred_i
                raw_upper_i = float(risk_i[1]) if len(risk_i) >= 2 else pred_i
                lower_i, upper_i = _normalize_interval_to_returns(
                    raw_lower_i,
                    raw_upper_i,
                    pred_i,
                    ref_price,
                )

                multi_horizon.append(
                    {
                        "horizon": mapped_horizon,
                        "predicted_return": pred_i,
                        "lower_return": lower_i,
                        "upper_return": upper_i,
                    }
                )

            for item in vol_results:
                if preferred and item.get("volatility_type") == preferred:
                    target = item
                    break
            if target is None:
                target = vol_results[0]

            pred_raw = float(target.get("predicted_return", 0.0))
            pred = _normalize_predicted_return(pred_raw, ref_price)

            risk = target.get("risk_interval") or [pred, pred]
            raw_lower = float(risk[0]) if len(risk) >= 2 else pred
            raw_upper = float(risk[1]) if len(risk) >= 2 else pred
            lower, upper = _normalize_interval_to_returns(
                raw_lower,
                raw_upper,
                pred,
                ref_price,
            )

            return {
                "median": pred,
                "upper": upper,
                "lower": lower,
                "confidence_score": float(target.get("confidence_score", 0.8)),
                "forecast_horizon": forecast_horizon,
                "model_version": str(parsed.get("model_version", self._model_id)),
                "multi_horizon_returns": sorted(multi_horizon, key=lambda x: int(x["horizon"])),
            }

        # 格式3：单值预测
        if "predicted_return" in parsed:
            pred = float(parsed.get("predicted_return", 0.0))
            risk = parsed.get("risk_interval") or [pred - 0.02, pred + 0.02]
            lower = float(risk[0]) if len(risk) >= 2 else pred - 0.02
            upper = float(risk[1]) if len(risk) >= 2 else pred + 0.02
            return {
                "median": pred,
                "upper": upper,
                "lower": lower,
                "confidence_score": float(parsed.get("confidence_score", 0.8)),
                "forecast_horizon": forecast_horizon,
                "model_version": str(parsed.get("model_version", self._model_id)),
            }

        raise RuntimeError("OpenAI 响应格式无法识别")

    def _parse_response(self, raw: dict, forecast_horizon: int) -> ModelRawResponse:
        """
        解析模型原始响应。

        Args:
            raw: 模型返回的原始字典。
            forecast_horizon: 预测步数（用于填充默认值）。

        Returns:
            ModelRawResponse 对象。
        """
        shap_data = raw.get("shap_values")
        shap_obj: Optional[ShapValues] = None

        if shap_data and isinstance(shap_data, dict):
            shap_obj = ShapValues(
                values=shap_data.get("values", {}),
                base_value=shap_data.get("base_value", 0.0),
            )

        return ModelRawResponse(
            median=float(raw.get("median", 0.0)),
            upper=float(raw.get("upper", 0.05)),
            lower=float(raw.get("lower", -0.05)),
            confidence_score=float(raw.get("confidence_score", 0.8)),
            shap_values=shap_obj,
            forecast_horizon=raw.get("forecast_horizon", forecast_horizon),
            model_version=raw.get("model_version"),
            multi_horizon_returns=[
                MultiHorizonReturnPoint(**item)
                for item in (raw.get("multi_horizon_returns") or [])
                if isinstance(item, dict)
            ],
        )

    async def health_check(self) -> bool:
        """
        检查云端模型服务是否可达。

        Returns:
            True 表示服务正常，False 表示不可达。
        """
        parsed = urlparse(self._predict_url)
        if self._mode == "openai":
            # 部分代理服务未实现 /models，允许 2xx/4xx 视为“可达”
            model_url = urlunparse(parsed._replace(path=(parsed.path.rsplit("/chat/completions", 1)[0] + "/models")))
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    resp = await client.get(model_url, headers=self._build_headers())
                    return resp.status_code < 500
            except Exception:
                return False

        health_path = parsed.path
        if health_path.endswith("/predict/returns"):
            health_path = health_path[: -len("/predict/returns")]
        health_url = urlunparse(parsed._replace(path=health_path.rstrip("/") + "/health"))
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(health_url)
                return resp.status_code == 200
        except Exception:
            return False

    async def mock_predict(
        self,
        feature_vector: dict,
        forecast_horizon: int = 5,
        include_shap: bool = True,
        current_price: Optional[float] = None,
    ) -> ModelRawResponse:
        """
        Mock 预测（用于云端模型不可用时的本地测试）。

        Args:
            feature_vector: 特征字典（仅用于计算 mock 数据）。
            forecast_horizon: 预测步数。
            include_shap: 是否生成 mock SHAP。

        Returns:
            ModelRawResponse mock 数据。
        """
        import random
        import math

        logger.warning("使用 MOCK 模式返回预测结果（开发/测试用）")

        base_return = random.gauss(0.001, 0.02)
        spread = abs(base_return) * 0.5 + 0.01

        mock_shap: Optional[ShapValues] = None
        if include_shap:
            top_features = list(feature_vector.keys())[:8]
            mock_shap = ShapValues(
                values={f: random.gauss(0, 0.005) for f in top_features},
                base_value=base_return * 0.1,
            )

        return ModelRawResponse(
            median=round(base_return, 6),
            upper=round(base_return + spread, 6),
            lower=round(base_return - spread, 6),
            confidence_score=round(random.uniform(0.65, 0.92), 3),
            shap_values=mock_shap,
            forecast_horizon=forecast_horizon,
            model_version="mock-v1.0",
        )
