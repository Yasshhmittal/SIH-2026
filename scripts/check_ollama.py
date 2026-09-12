"""Diagnose the Ollama client's health check."""

import traceback

from prahari.llm.ollama import get_client

client = get_client()
print(f"client base_url : {client._client.base_url}")

try:
    response = client._client.get("/api/tags", timeout=3.0)
    print(f"raw status      : {response.status_code}")
    print(f"model count     : {len(response.json().get('models', []))}")
except Exception:
    print("raw request failed:")
    traceback.print_exc()

print(f"client.health() : {client.health()}")

try:
    loaded = client.loaded_models()
    print(f"loaded_models() : {loaded}")
except Exception as exc:
    print(f"loaded_models() raised: {type(exc).__name__}: {exc}")
