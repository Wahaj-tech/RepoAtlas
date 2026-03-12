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

    KEEP_EXTENSIONS = [".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rb", ".java"]

    skip_folders = [
        "test", "tests", "docs", "doc",
        "examples", "__pycache__", ".github",
        "benchmark", "benchmarks", "migrations",
        "build", "dist", "vendor"
    ]

    def should_skip(filepath):
        ext = "." + filepath.split(".")[-1] if "." in filepath else ""
        if ext not in KEEP_EXTENSIONS:
            return True

        path_lower = filepath.lower()
        parts = path_lower.replace("\\", "/").split("/")

        for part in parts[:-1]:
            for skip in skip_folders:
                if skip in part:
                    return True

        filename = parts[-1]
        if filename.startswith("test_"):
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