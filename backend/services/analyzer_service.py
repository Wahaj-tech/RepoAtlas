from services.github_service import (
    fetch_repo_tree,
    fetch_file_content,
    fetch_issues,
    fetch_repo_metadata
)
import asyncio

async def analyze_repo(owner: str, repo: str, user_profile: dict):
    metadata = await fetch_repo_metadata(owner, repo)
    file_tree = await fetch_repo_tree(owner, repo)

    # Filter out non-core files before fetching
    skip_folders = [
        "test", "tests", "docs", "doc",
        "examples", "__pycache__", ".github",
        "benchmark", "benchmarks", "migrations",
        "static", "templates", "build", "dist"
    ]

    def should_skip(filepath):
        path_lower = filepath.lower()
        parts = path_lower.replace("\\", "/").split("/")
        for part in parts:
            for skip in skip_folders:
                if skip in part:
                    return True
        return False

    filtered_tree = [f for f in file_tree if not should_skip(f["path"])]
    important_files = filtered_tree[:40]
    file_contents = {}

    for file in important_files:
        content = await fetch_file_content(owner, repo, file["path"])
        file_contents[file["path"]] = content
        await asyncio.sleep(0.1)

    issues = await fetch_issues(owner, repo)

    return {
        "metadata": metadata,
        "file_tree": file_tree,
        "file_contents": file_contents,
        "issues": issues,
        "user_profile": user_profile
    }