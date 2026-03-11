from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.repo import router as repo_router

app = FastAPI(title="RepoAtlas API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repo_router, prefix="/api")

@app.get("/health")
def health():
    return {"status": "ok", "message": "RepoAtlas is running"}