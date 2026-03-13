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


async def check_rate_limit(client: httpx.AsyncClient):
    try:
        response = await client.get(
            f"{BASE_URL}/rate_limit",
            headers=HEADERS,
        )
        data = response.json() if response.status_code == 200 else {}
        remaining = data.get("rate", {}).get("remaining", 0)
        print(f"GitHub API calls remaining: {remaining}")
        if remaining < 10:
            print("WARNING: Rate limit almost hit!")
        return remaining
    except Exception as e:
        print(f"Rate limit check failed: {e}")
        return 0

async def fetch_repo_metadata(owner: str, repo: str):
    url = f"{BASE_URL}/repos/{owner}/{repo}"
    try:
        async with httpx.AsyncClient() as client:
            await check_rate_limit(client)
            response = await client.get(url, headers=HEADERS)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"Error fetching metadata for {owner}/{repo}: {e}")
        return {
            "name": repo,
            "description": "",
            "stargazers_count": 0,
            "language": "Unknown",
        }

async def fetch_repo_tree(owner: str, repo: str):
    url = f"{BASE_URL}/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"
    try:
        async with httpx.AsyncClient() as client:
            await check_rate_limit(client)
            response = await client.get(url, headers=HEADERS)
            response.raise_for_status()
            data = response.json()
            tree = data.get("tree", [])
            return [
                f for f in tree
                if f.get("type") == "blob"
                and not any(skip in f.get("path", "") for skip in [
                    "node_modules", ".git", "__pycache__",
                    "dist", "build", ".env", "vendor"
                ])
                and f.get("path", "").endswith((
                    ".py", ".js", ".ts", ".jsx", ".tsx",
                    ".go", ".java", ".cpp", ".c", ".rb"
                ))
            ]
    except Exception as e:
        print(f"Error fetching repo tree for {owner}/{repo}: {e}")
        return []

async def fetch_file_content(owner: str, repo: str, path: str):
    url = f"{BASE_URL}/repos/{owner}/{repo}/contents/{path}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=HEADERS)
            if response.status_code >= 400:
                return ""
            data = response.json()
            if "content" in data:
                return base64.b64decode(
                    data["content"]
                ).decode("utf-8", errors="ignore")
            return ""
    except Exception as e:
        print(f"Error fetching file content {owner}/{repo}/{path}: {e}")
        return ""

async def fetch_issues(owner: str, repo: str):
    url = f"{BASE_URL}/repos/{owner}/{repo}/issues"
    params = {
        "state": "open",
        "per_page": 50,
        "labels": "good first issue"
    }
    try:
        async with httpx.AsyncClient() as client:
            await check_rate_limit(client)
            response = await client.get(url, headers=HEADERS, params=params)
            issues = response.json() if response.status_code == 200 else []

            if not isinstance(issues, list) or not issues:
                params.pop("labels", None)
                response = await client.get(
                    url, headers=HEADERS, params=params
                )
                issues = response.json() if response.status_code == 200 else []

            if not isinstance(issues, list):
                return []

            return issues
    except Exception as e:
        print(f"Error fetching issues for {owner}/{repo}: {e}")
        return []


async def fetch_repo_languages(owner: str, repo: str, client: httpx.AsyncClient):
    url = f"{BASE_URL}/repos/{owner}/{repo}/languages"
    try:
        response = await client.get(url, headers=HEADERS)
        if response.status_code >= 400:
            return []

        data = response.json()
        if not isinstance(data, dict):
            return []

        sorted_langs = sorted(
            data.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        return [lang for lang, _ in sorted_langs[:5]]
    except Exception:
        return []


async def fetch_repo_data(github_url: str):
    try:
        clean_url = github_url.strip().rstrip("/").replace(".git", "").lower()
        if "github.com/" not in clean_url:
            raise ValueError("Invalid GitHub URL")

        parts = clean_url.split("github.com/")[-1].split("/")
        if len(parts) < 2:
            raise ValueError("Invalid GitHub URL")

        owner = parts[0]
        repo = parts[1]

        metadata = await fetch_repo_metadata(owner, repo)
        file_tree = await fetch_repo_tree(owner, repo)
        issues = await fetch_issues(owner, repo)

        return {
            "metadata": {
                "name": metadata.get("name", repo),
                "description": metadata.get("description", ""),
                "stars": metadata.get("stargazers_count", 0),
                "language": metadata.get("language", "Unknown"),
            },
            "file_tree": file_tree,
            "issues": issues,
        }
    except Exception as e:
        print(f"Error fetching {github_url}: {e}")
        return {
            "metadata": {
                "name": github_url.split("/")[-1],
                "description": "",
                "stars": 0,
                "language": "Unknown"
            },
            "file_tree": [],
            "issues": []
        }