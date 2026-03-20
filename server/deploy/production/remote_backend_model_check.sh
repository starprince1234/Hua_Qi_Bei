#!/usr/bin/env bash
set -e

echo '===BACKEND_TO_MODEL_URLLIB===' 
docker exec huaqibei_prod-backend-1 /bin/sh -lc "python - <<'PY'
import urllib.request
url='http://host.docker.internal:6006/v1/models'
try:
    with urllib.request.urlopen(url, timeout=10) as r:
        data = r.read(300)
        print('status=', r.status)
        print(data.decode('utf-8', errors='ignore'))
except Exception as e:
    print('error=', repr(e))
    raise
PY"
