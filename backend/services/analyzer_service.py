from services.github_service import (
    fetch_repo_tree,
    fetch_file_content,
    fetch_issues,
    fetch_repo_metadata
)
import asyncio
import time

_raw_repo_cache = {}
_repo_file_content_cache = {}

MAX_CONTENT_FILES = 15
MIN_FILE_SIZE = 500


def _select_important_files(file_tree):
    priority_names = ("main", "app", "index", "core", "init")

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

    filtered = []
    for f in file_tree:
        path = f.get("path", "")
        size = f.get("size", 0)
        if should_skip(path) or size < MIN_FILE_SIZE:
            continue

        normalized = path.replace("\\", "/")
        parts = normalized.split("/")
        filename = parts[-1].lower()
        base_name = filename.rsplit(".", 1)[0]

        is_root = len(parts) == 1
        has_priority_name = any(name in base_name for name in priority_names)

        filtered.append(
            {
                **f,
                "_rank": (
                    0 if is_root else 1,
                    0 if has_priority_name else 1,
                    -size,
                ),
            }
        )

    filtered.sort(key=lambda x: x["_rank"])
    selected = filtered[:MAX_CONTENT_FILES]
    print(f"[AnalyzeRepo] Selected {len(selected)} important files (max {MAX_CONTENT_FILES}).")
    return selected


async def _timed_call(label, coro):
    start = time.perf_counter()
    result = await coro
    duration = time.perf_counter() - start
    print(f"[Timing] {label}: {duration:.2f}s")
    return result, duration


async def _fetch_contents_parallel(owner, repo, files, repo_cache):
    file_contents = {}
    semaphore = asyncio.Semaphore(8)

    async def _load(path):
        if path in repo_cache:
            return path, repo_cache[path]
        async with semaphore:
            content = await fetch_file_content(owner, repo, path)
            repo_cache[path] = content
            return path, content

    tasks = [_load(f["path"]) for f in files]
    results = await asyncio.gather(*tasks)
    for path, content in results:
        file_contents[path] = content

    return file_contents

async def analyze_repo(owner: str, repo: str, user_profile: dict):
    repo_key = f"{owner}/{repo}".lower()
    total_start = time.perf_counter()

    if repo_key in _raw_repo_cache:
        cached = _raw_repo_cache[repo_key]
        metadata = cached["metadata"]
        file_tree = cached["file_tree"]
        issues = cached["issues"]
        print(f"[AnalyzeRepo] Using raw GitHub cache for {repo_key}.")
    else:
        (metadata, _), (file_tree, _), (issues, _) = await asyncio.gather(
            _timed_call("GitHub metadata fetch", fetch_repo_metadata(owner, repo)),
            _timed_call("GitHub file tree fetch", fetch_repo_tree(owner, repo)),
            _timed_call("GitHub issues fetch", fetch_issues(owner, repo)),
        )

        _raw_repo_cache[repo_key] = {
            "metadata": metadata,
            "file_tree": file_tree,
            "issues": issues,
        }

    important_files = _select_important_files(file_tree)
    repo_content_cache = _repo_file_content_cache.setdefault(repo_key, {})

    content_start = time.perf_counter()
    file_contents = await _fetch_contents_parallel(
        owner,
        repo,
        important_files,
        repo_content_cache,
    )
    print(f"[Timing] File contents fetch: {time.perf_counter() - content_start:.2f}s")
    print(f"[Timing] analyze_repo total: {time.perf_counter() - total_start:.2f}s")

    return {
        "metadata": metadata,
        "file_tree": file_tree,
        "file_contents": file_contents,
        "issues": issues,
        "user_profile": user_profile
    }