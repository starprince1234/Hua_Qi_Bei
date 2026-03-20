#!/usr/bin/env bash
set -e

echo '===BACKEND_CHAT_COMPLETIONS_PROBE===' 
docker exec huaqibei_prod-backend-1 /bin/sh -lc "python - <<'PY'
import json, urllib.request
url='http://host.docker.internal:6006/v1/chat/completions'
payload={
  'model':'oil_vol_model',
  'messages':[{'role':'user','content':'hello'}],
  'temperature':0.1
}
req=urllib.request.Request(url,data=json.dumps(payload).encode('utf-8'),headers={'Content-Type':'application/json'},method='POST')
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        b=r.read(400)
        print('status=',r.status)
        print(b.decode('utf-8',errors='ignore'))
except Exception as e:
    print('error=',repr(e))
    if hasattr(e,'read'):
        try:
            print(e.read(400).decode('utf-8',errors='ignore'))
        except Exception:
            pass
PY"
