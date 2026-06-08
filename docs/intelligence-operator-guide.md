# Intelligence Operator Guide

This guide covers the news events, backtest validation, and factor history intelligence extensions.

## Demo mode

Use demo mode for local development, competition demos, and offline checks:

```env
NEWS_PROVIDER=mock
```

- No GCP, NewsAPI, PostgreSQL, or Redis credentials are required.
- The backend serves deterministic fixture data from the repository.
- Responses should report honest provider status such as `demo`.
- Leave `DATABASE_URL`, `REDIS_URL`, `GDELT_BIGQUERY_PROJECT_ID`, `GDELT_GOOGLE_CREDENTIALS_JSON`, and `NEWSAPI_API_KEY` as placeholders.

## Live provider modes

Live modes are backend-only. The frontend should only know `NEXT_PUBLIC_API_URL`; it must never hold BigQuery, NewsAPI, database, Redis, model, or LLM credentials.

| Mode | Use when | Required backend configuration |
| --- | --- | --- |
| `gdelt` | GDELT BigQuery is the primary source | `GDELT_BIGQUERY_PROJECT_ID`, `GDELT_GOOGLE_CREDENTIALS_JSON`, `GDELT_BIGQUERY_MAX_BYTES_BILLED` |
| `newsapi` | NewsAPI is the temporary news source | `DATABASE_URL`, `NEWSAPI_API_KEY` |
| `hybrid` | GDELT should be tried first, then NewsAPI fallback | `GDELT_BIGQUERY_PROJECT_ID`, `GDELT_GOOGLE_CREDENTIALS_JSON`, `GDELT_BIGQUERY_MAX_BYTES_BILLED`, `NEWSAPI_API_KEY` |

Optional cache/scheduler settings:

```env
REDIS_URL=redis://localhost:6379/0
CACHE_TTL_SECONDS=3600
NEWS_REFRESH_INTERVAL_MINUTES=30
```

## Switching modes

1. Keep `NEWS_PROVIDER=mock` for no-credential demos.
2. Store real `DATABASE_URL`, `REDIS_URL`, `GDELT_BIGQUERY_PROJECT_ID`, `GDELT_GOOGLE_CREDENTIALS_JSON`, and `NEWSAPI_API_KEY` in Doppler or the deployment secret manager, not in Git.
3. Change `NEWS_PROVIDER` to `gdelt`, `newsapi`, or `hybrid` in the backend environment.
4. Restart the backend or Docker Compose stack so settings reload.
5. Check API payloads for explicit `provider_status` values such as `gdelt_live`, `newsapi_live`, `hybrid_live`, or `demo`; live providers should fall back gracefully instead of returning blank panels.

## Doppler field sources

| Key | Where to find the value |
| --- | --- |
| `NEWS_PROVIDER` | Choose the desired mode in this guide: `mock`, `newsapi`, `gdelt`, or `hybrid`. Use `hybrid` when both GDELT and NewsAPI are configured. |
| `NEWSAPI_API_KEY` | NewsAPI dashboard at `https://newsapi.org/`; use the API key shown in your account, then rotate it if it has been exposed in chat or screenshots. |
| `GDELT_BIGQUERY_PROJECT_ID` | The `project_id` field in the downloaded Google service account JSON, or the GCP project page created in the GDELT setup tutorial. |
| `GDELT_GOOGLE_CREDENTIALS_JSON` | The full contents of the downloaded Google service account JSON file. Store it as one Doppler secret; do not place this JSON in the repo. |
| `GDELT_BIGQUERY_MAX_BYTES_BILLED` | Use `1073741824` for the tutorial default, or set a stricter production budget. |
| `DATABASE_URL` | Future PostgreSQL cache connection string from your deployment database provider. Leave as a placeholder until cache persistence is implemented. |
| `REDIS_URL` | Future Redis cache URL from your deployment cache provider. Leave as a placeholder until Redis caching is implemented. |
