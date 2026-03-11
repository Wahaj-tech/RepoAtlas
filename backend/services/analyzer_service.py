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
    
    # fetch only top 30 files
    important_files = file_tree[:30]
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