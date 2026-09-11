"""Dev server runner."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.prahari.main:app",
        host="127.0.0.1",
        port=8077,
        reload=True,
        reload_dirs=["backend"]
    )
