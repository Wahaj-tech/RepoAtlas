import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from routers.repo import router as repo_router

app = FastAPI(title="RepoAtlas API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repo_router, prefix="/api")

# ── Serve React frontend (built files copied to ./static by Docker) ──
STATIC_DIR = Path(__file__).resolve().parent / "static"

if STATIC_DIR.is_dir():
    # Mount assets (JS/CSS/images) — but NOT at "/" to avoid shadowing API routes
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/")
    def root():
        return FileResponse(STATIC_DIR / "index.html")

    # Catch-all for client-side routing (e.g. /dashboard, /repo/xyz)
    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")
else:
    # Local dev — no built frontend, redirect to Swagger docs
    @app.get("/")
    def root():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/docs")

@app.get("/health")
def health():
    return {"status": "ok", "message": "RepoAtlas is running"}