import http.client

try:
    conn = http.client.HTTPConnection("localhost", 4200, timeout=5)
    conn.request("GET", "/api/health")
    resp = conn.getresponse()
    if resp.status == 200:
        exit(0)
    else:
        exit(1)
except Exception:
    exit(1)
