from __future__ import annotations

import uvicorn

from server.settings import host, port


if __name__ == "__main__":
    uvicorn.run("server.app:app", host=host(), port=port(), reload=False)
