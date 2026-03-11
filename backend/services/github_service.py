import httpx
import base64
import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}
BASE_URL = "https://api.github.com"

async def fetch_repo_metadata(owner: str, repo: str):
    url = f"{BASE_URL}/repos/{owner}/{repo}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=HEADERS)
        return response.json()

async def fetch_repo_tree(owner: str, repo: str):
    url = f"{BASE_URL}/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=HEADERS)
        data = response.json()
        tree = data.get("tree", [])
        return [
            f for f in tree
            if f["type"] == "blob"
            and not any(skip in f["path"] for skip in [
                "node_modules", ".git", "__pycache__",
                "dist", "build", ".env", "vendor"
            ])
            and f["path"].endswith((
                ".py", ".js", ".ts", ".jsx", ".tsx",
                ".go", ".java", ".cpp", ".c", ".rb"
            ))
        ]

async def fetch_file_content(owner: str, repo: str, path: str):
    url = f"{BASE_URL}/repos/{owner}/{repo}/contents/{path}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=HEADERS)
        data = response.json()
        if "content" in data:
            return base64.b64decode(
                data["content"]
            ).decode("utf-8", errors="ignore")
        return ""

async def fetch_issues(owner: str, repo: str):
    url = f"{BASE_URL}/repos/{owner}/{repo}/issues"
    params = {
        "state": "open",
        "per_page": 50,
        "labels": "good first issue"
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=HEADERS, params=params)
        issues = response.json()
        if not issues:
            params.pop("labels")
            response = await client.get(
                url, headers=HEADERS, params=params
            )
            issues = response.json()
        return issues