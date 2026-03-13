import httpx
import base64
import os
import asyncio
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
BASE_URL = "https://api.github.com"
REQUEST_TIMEOUT = httpx.Timeout(20.0, connect=10.0)


def _build_headers() -> dict:
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "RepoAtlas/1.0",
    }
    if GITHUB_TOKEN and GITHUB_TOKEN.strip().lower() != "none":
        headers["Authorization"] = f"token {GITHUB_TOKEN.strip()}"
    return headers


HEADERS = _build_headers()


def _new_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=HEADERS)


def _extract_owner_repo(github_url: str):
    raw_url = (github_url or "").strip()
    if not raw_url:
        raise ValueError("Empty GitHub URL")

    normalized = raw_url.rstrip("/")

    # Support shorthand input like owner/repo.
    if "github.com" not in normalized.lower() and "/" in normalized:
        parts = [p for p in normalized.split("/") if p]
        if len(parts) >= 2:
            return parts[0], parts[1].replace(".git", "")

    if not normalized.lower().startswith(("http://", "https://")):
        normalized = f"https://{normalized}"

    parsed = urlparse(normalized)
    if "github.com" not in parsed.netloc.lower():
        raise ValueError("Invalid GitHub URL")

    path_parts = [p for p in parsed.path.split("/") if p]
    if len(path_parts) < 2:
        raise ValueError("Invalid GitHub URL")

    owner = path_parts[0]
    repo = path_parts[1].replace(".git", "")
    return owner, repo


def _fallback_repo_name(github_url: str) -> str:
    try:
        owner, repo = _extract_owner_repo(github_url)
        return repo or owner
    except Exception:
        return (github_url or "unknown-repo").rstrip("/").split("/")[-1] or "unknown-repo"


async def check_rate_limit(client: httpx.AsyncClient):
    try:
        response = await client.get(
            f"{BASE_URL}/rate_limit",
        )
        data = response.json() if response.status_code == 200 else {}
        rate = data.get("rate", {}) if isinstance(data, dict) else {}
        remaining = rate.get("remaining", 0)
        print(f"GitHub API calls remaining: {remaining}")
        if remaining < 10:
            print("WARNING: Rate limit almost hit!")
        return remaining
    except Exception as e:
        print(f"Rate limit check failed: {e}")
        return 0

async def fetch_repo_metadata(owner: str, repo: str, client: httpx.AsyncClient | None = None):
    url = f"{BASE_URL}/repos/{owner}/{repo}"
    own_client = client is None
    client = client or _new_client()
    try:
        await check_rate_limit(client)
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"Error fetching metadata for {owner}/{repo}: {e}")
        return {
            "name": repo,
            "description": "",
            "stargazers_count": 0,
            "language": "Unknown",
        }
    finally:
        if own_client:
            await client.aclose()

async def fetch_repo_tree(owner: str, repo: str, client: httpx.AsyncClient | None = None):
    url = f"{BASE_URL}/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"
    own_client = client is None
    client = client or _new_client()
    try:
        await check_rate_limit(client)
        response = await client.get(url)
        response.raise_for_status()
        data = response.json() if response.status_code == 200 else {}
        tree = data.get("tree", []) if isinstance(data, dict) else []
        return [
            f for f in tree
            if isinstance(f, dict)
            and f.get("type") == "blob"
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
    finally:
        if own_client:
            await client.aclose()

async def fetch_file_content(owner: str, repo: str, path: str, client: httpx.AsyncClient | None = None):
    url = f"{BASE_URL}/repos/{owner}/{repo}/contents/{path}"
    own_client = client is None
    client = client or _new_client()
    try:
        response = await client.get(url)
        if response.status_code >= 400:
            return ""
        data = response.json()
        if not isinstance(data, dict):
            return ""
        if data.get("encoding") == "base64" and data.get("content"):
            return base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
        return data.get("content", "") if isinstance(data.get("content"), str) else ""
    except Exception as e:
        print(f"Error fetching file content {owner}/{repo}/{path}: {e}")
        return ""
    finally:
        if own_client:
            await client.aclose()

async def fetch_issues(owner: str, repo: str, client: httpx.AsyncClient | None = None):
    url = f"{BASE_URL}/repos/{owner}/{repo}/issues"
    params = {
        "state": "open",
        "per_page": 50,
        "sort": "updated",
        "direction": "desc",
    }
    own_client = client is None
    client = client or _new_client()
    try:
        await check_rate_limit(client)
        response = await client.get(url, params=params)
        if response.status_code >= 400:
            print(f"Issues fetch failed for {owner}/{repo}: HTTP {response.status_code}")
            return []

        payload = response.json()
        if not isinstance(payload, list):
            return []

        issues = [
            i for i in payload
            if isinstance(i, dict)
            and not i.get("pull_request")
            and "/pull/" not in str(i.get("html_url", ""))
        ]
        print(f"Real issues fetched: {len(issues)}")
        return issues
    except Exception as e:
        print(f"Error fetching issues: {e}")
        return []
    finally:
        if own_client:
            await client.aclose()


async def fetch_repo_languages(owner: str, repo: str, client: httpx.AsyncClient | None = None):
    url = f"{BASE_URL}/repos/{owner}/{repo}/languages"
    own_client = client is None
    client = client or _new_client()
    try:
        response = await client.get(url)
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
    finally:
        if own_client:
            await client.aclose()


async def fetch_repo_data(github_url: str):
    try:
        owner, repo = _extract_owner_repo(github_url)

        async with _new_client() as client:
            metadata_result, file_tree_result, issues_result = await asyncio.gather(
                fetch_repo_metadata(owner, repo, client=client),
                fetch_repo_tree(owner, repo, client=client),
                fetch_issues(owner, repo, client=client),
                return_exceptions=True,
            )

        metadata = metadata_result if isinstance(metadata_result, dict) else {}
        file_tree = file_tree_result if isinstance(file_tree_result, list) else []
        issues = issues_result if isinstance(issues_result, list) else []

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
                "name": _fallback_repo_name(github_url),
                "description": "",
                "stars": 0,
                "language": "Unknown"
            },
            "file_tree": [],
            "issues": []
        }