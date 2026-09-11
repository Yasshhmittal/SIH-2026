import urllib.request
import json

req = urllib.request.Request(
    'http://127.0.0.1:8077/api/runs', 
    data=b'{"prompt":"hello", "org_id":"mrpl"}', 
    headers={'Content-Type': 'application/json'}
)
res = urllib.request.urlopen(req)
run = json.loads(res.read())
print("Run started:", run)

url = f'http://127.0.0.1:8077/api/runs/{run["run_id"]}/events'
print("Fetching events from:", url)
req2 = urllib.request.Request(url)
res2 = urllib.request.urlopen(req2)
for i in range(5):
    print("Event:", res2.readline())
