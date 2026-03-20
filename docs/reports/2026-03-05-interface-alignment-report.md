# Interface Alignment Report

> **Date:** 2026-03-05  
> **Environment:** Development  
> **Reviewer:** Platform Engineering  
> **Branch:** `copilot/full-sync-excluding-xlsx`

---

## Overview

This report documents the alignment between frontend API calls (defined in `frontend/src/components/apiBase.ts` and the component files) and the backend orchestrator endpoints (defined in `orchestratoropenapi.yaml` and implemented in `backend/huaqibei/oil-risk-orchestrator/app/api/routes/`).

---

## Endpoint Alignment Matrix

| Frontend Call | Backend Endpoint | Method | Status |
|---|---|---|---|
| `POST /api/upload` | `POST /upload` | multipart/form-data | ✅ Aligned |
| `POST /api/predict` | `POST /predict` | application/json | ✅ Aligned |
| `GET /api/report/:fileId` | `GET /report/{file_id}` | — | ✅ Aligned |
| `GET /api/health` | `GET /health` | — | ✅ Aligned |

---

## Upload Endpoint

### Frontend Request (`FileUploader.tsx`)

```typescript
const formData = new FormData();
formData.append("file", selectedFile);
const response = await fetch("/api/upload", {
  method: "POST",
  body: formData,
});
```

### Backend Endpoint (`POST /upload`)

```python
@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)) -> UploadResponse:
    ...
```

### Request Schema Alignment

| Frontend Field | Backend Field | Type | Aligned |
|---|---|---|---|
| `file` (FormData key) | `file: UploadFile` | multipart | ✅ |

### Response Schema Alignment

| Frontend Expectation | Backend Field | Type | Aligned |
|---|---|---|---|
| `response.success` | `UploadResponse.success` | `bool` | ✅ |
| `response.data.file_id` | `UploadData.file_id` | `str` | ✅ |
| `response.data.filename` | `UploadData.filename` | `str` | ✅ |
| `response.data.size` | `UploadData.size` | `int` | ✅ |
| `response.data.preview` | `UploadData.preview` | `list[dict]` | ✅ |

---

## Predict Endpoint

### Frontend Request (`PredictForm.tsx`)

```typescript
const payload = {
  file_id: fileId,
  horizon: selectedHorizon,         // number: 1|3|7|14|30
  include_explainability: true,
  include_knowledge_graph: false,
  report_style: selectedStyle,      // "banking" | "general"
  industries: selectedIndustries,   // string[]
};
const response = await fetch("/api/predict", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(payload),
});
```

### Backend Schema (`PredictRequest`)

```python
class PredictRequest(BaseModel):
    file_id: str
    horizon: Literal[1, 3, 7, 14, 30]
    include_explainability: bool = True
    include_knowledge_graph: bool = False
    report_style: Literal["banking", "general"] = "general"
    industries: list[str] = [...]
```

### Request Schema Alignment

| Frontend Field | Backend Field | Type | Aligned |
|---|---|---|---|
| `file_id` | `file_id` | `string / str` | ✅ |
| `horizon` | `horizon` | `number / Literal[1,3,7,14,30]` | ✅ |
| `include_explainability` | `include_explainability` | `boolean / bool` | ✅ |
| `include_knowledge_graph` | `include_knowledge_graph` | `boolean / bool` | ✅ |
| `report_style` | `report_style` | `string / Literal` | ✅ |
| `industries` | `industries` | `string[] / list[str]` | ✅ |

### Response Schema Alignment (`PredictionResponse`)

| Frontend Expectation | Backend Field | Type | Aligned |
|---|---|---|---|
| `result.predictions` | `predictions` | `number[] / list[float]` | ✅ |
| `result.quantiles` | `quantiles` | `Record<string, number[]>` | ✅ |
| `result.risk_level` | `risk_level` | `"low"\|"medium"\|"high"\|"extreme"` | ✅ |
| `result.var_95` | `var_95` | `number / float` | ✅ |
| `result.cvar_95` | `cvar_95` | `number / float` | ✅ |
| `result.volatility` | `volatility` | `number / float` | ✅ |
| `result.factor_contributions` | `factor_contributions` | `FactorContribution[]` | ✅ |
| `result.industry_impacts` | `industry_impacts` | `IndustryImpactResult[]` | ✅ |
| `result.ai_insight` | `ai_insight` | `string / str` | ✅ |

---

## Report Endpoint

### Frontend Request (`ResultDisplay.tsx`)

```typescript
const response = await fetch(`/api/report/${fileId}?style=${style}`);
```

### Backend Endpoint (`GET /report/{file_id}`)

```python
@router.get("/report/{file_id}", response_model=ReportResponse)
async def get_report(file_id: str, style: str = "general") -> ReportResponse:
    ...
```

### Response Schema Alignment

| Frontend Expectation | Backend Field | Type | Aligned |
|---|---|---|---|
| `report.title` | `title` | `string / str` | ✅ |
| `report.summary.content` | `summary.content` | `string / str` | ✅ |
| `report.detail.content` | `detail.content` | `string / str` | ✅ |
| `report.charts` | `charts` | `object[] / list[dict]` | ✅ |
| `report.generated_at` | `generated_at` | `string (ISO 8601)` | ✅ |

---

## Known Gaps / Action Items

| # | Gap | Owner | Priority | Ticket |
|---|---|---|---|---|
| 1 | `style` query param not forwarded in report route handler | Backend | Medium | #42 |
| 2 | Frontend `FactorContribution` type missing `category` field rendering | Frontend | Low | #43 |
| 3 | `include_knowledge_graph=true` path not yet wired to `transmission_mapper` | Backend | Medium | #44 |

---

## Conclusion

The frontend and backend interfaces are **substantially aligned** for all primary user flows (upload → predict → report). Three minor gaps have been identified and are tracked in the issue backlog. No breaking mismatches were found.
