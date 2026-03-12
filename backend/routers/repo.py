from fastapi import APIRouter, HTTPException
from models.schemas import (
    AnalyzeRequest, ImpactRequest,
    MatchIssuesRequest, ContributionPathRequest,
    AnalyzeIssueRequest, GeneratePathRequest,
)
from services.analyzer_service import analyze_repo
from services.graph_service import build_graph, get_impact, export_graph
from services.cache_service import get_cache, set_cache
from services.ai_service import get_recommendations, match_issues, get_contribution_path
from services.github_service import fetch_issues, fetch_repo_metadata
from services.issue_matcher import analyze_issue
from services.contribution_path import generate_path

router = APIRouter()

def parse_github_url(url: str):
    parts = url.rstrip("/").split("/")
    return parts[-2], parts[-1]

@router.post("/analyze")
async def analyze(request: AnalyzeRequest):
    try:
        owner, repo = parse_github_url(request.github_url)

        cache_key = f"{owner}_{repo}_{request.user_profile.experience}"
        cached = get_cache(cache_key)
        if cached:
            return cached

        repo_data = await analyze_repo(
            owner, repo, request.user_profile.dict()
        )

        graph = build_graph(
            repo_data["file_tree"],
            repo_data["file_contents"]
        )
        graph_json = export_graph(graph)

        recommendations = await get_recommendations(
            repo_data["issues"],
            graph_json,
            request.user_profile.dict()
        )

        result = {
            "metadata": {
                "name": repo_data["metadata"].get("name"),
                "description": repo_data["metadata"].get("description"),
                "stars": repo_data["metadata"].get("stargazers_count"),
                "language": repo_data["metadata"].get("language"),
            },
            "graph": graph_json,
            "recommendations": recommendations,
            "issues": repo_data["issues"][:10],
        }

        set_cache(cache_key, result)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/match-issues")
async def match_issues_endpoint(request: MatchIssuesRequest):
    """
    AI-powered issue matching: pre-filters issues algorithmically
    by language overlap, difficulty fit, and interests, then asks
    the AI to rank and explain the best matches.
    """
    try:
        owner, repo = parse_github_url(request.github_url)

        # Check cache (include label filter in key)
        label_key = "_".join(sorted(request.label_filter or []))
        cache_key = f"match_{owner}_{repo}_{request.user_profile.experience}_{label_key}"
        cached = get_cache(cache_key)
        if cached:
            return cached

        repo_data = await analyze_repo(
            owner, repo, request.user_profile.dict()
        )

        graph = build_graph(
            repo_data["file_tree"],
            repo_data["file_contents"]
        )
        graph_json = export_graph(graph)

        matches = await match_issues(
            repo_data["issues"],
            graph_json,
            request.user_profile.dict(),
            max_results=request.max_results,
            label_filter=request.label_filter,
        )

        result = {
            "matches": matches,
            "total_issues_scanned": len(repo_data["issues"]),
            "repo": f"{owner}/{repo}",
        }

        set_cache(cache_key, result)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/contribution-path")
async def contribution_path_endpoint(request: ContributionPathRequest):
    """
    Generate a step-by-step contribution guide for a specific issue,
    tailored to the user's experience level and known languages.
    """
    try:
        owner, repo = parse_github_url(request.github_url)

        cache_key = f"path_{owner}_{repo}_{request.issue_number}_{request.user_profile.experience}"
        cached = get_cache(cache_key)
        if cached:
            return cached

        repo_data = await analyze_repo(
            owner, repo, request.user_profile.dict()
        )

        # Find the specific issue
        target_issue = None
        for issue in repo_data["issues"]:
            if issue.get("number") == request.issue_number:
                target_issue = issue
                break

        if not target_issue:
            # Fetch it directly if not in the issues list
            issues = await fetch_issues(owner, repo)
            for issue in issues:
                if issue.get("number") == request.issue_number:
                    target_issue = issue
                    break

        if not target_issue:
            raise HTTPException(
                status_code=404,
                detail=f"Issue #{request.issue_number} not found in {owner}/{repo}"
            )

        graph = build_graph(
            repo_data["file_tree"],
            repo_data["file_contents"]
        )
        graph_json = export_graph(graph)

        path = await get_contribution_path(
            target_issue,
            graph_json,
            request.user_profile.dict(),
        )

        result = {
            "issue": {
                "number": target_issue.get("number"),
                "title": target_issue.get("title"),
                "url": target_issue.get("html_url"),
                "labels": [l["name"] for l in target_issue.get("labels", [])],
            },
            "contribution_path": path,
            "repo": f"{owner}/{repo}",
        }

        set_cache(cache_key, result)
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── AI Layer Endpoints ───────────────────────────────────────────────────────

@router.post("/analyze-issue")
async def analyze_issue_endpoint(request: AnalyzeIssueRequest):
    """
    Issue Matching Engine — Maps a GitHub issue to relevant codebase files.

    Pipeline:
    1. Extract keywords from issue title, body, labels
    2. Match keywords against files, classes, functions in the knowledge graph
    3. Expand matches through graph dependencies
    4. Apply centrality boost for high-connectivity files
    5. Refine with LLM for scoring + difficulty estimate

    Returns matched files with relevance scores, difficulty, and estimated time.
    """
    try:
        owner, repo = parse_github_url(request.github_url)

        cache_key = f"ai_issue_{owner}_{repo}_{request.issue_number}"
        cached = get_cache(cache_key)
        if cached:
            return cached

        repo_data = await analyze_repo(owner, repo, {})

        # Find the target issue
        target_issue = None
        for issue in repo_data["issues"]:
            if issue.get("number") == request.issue_number:
                target_issue = issue
                break

        if not target_issue:
            issues = await fetch_issues(owner, repo)
            for issue in issues:
                if issue.get("number") == request.issue_number:
                    target_issue = issue
                    break

        if not target_issue:
            raise HTTPException(
                status_code=404,
                detail=f"Issue #{request.issue_number} not found in {owner}/{repo}",
            )

        # Build the knowledge graph
        graph = build_graph(
            repo_data["file_tree"],
            repo_data["file_contents"],
        )

        issue_labels = [l["name"] for l in target_issue.get("labels", [])]

        # Run the issue matching pipeline
        result = await analyze_issue(
            issue_title=target_issue.get("title", ""),
            issue_body=target_issue.get("body") or "",
            issue_labels=issue_labels,
            graph=graph,
            file_contents=repo_data["file_contents"],
        )

        result["repo"] = f"{owner}/{repo}"
        result["issue_number"] = request.issue_number
        result["issue_url"] = target_issue.get("html_url", "")

        set_cache(cache_key, result)
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-path")
async def generate_path_endpoint(request: GeneratePathRequest):
    """
    Contribution Path Generator — Step-by-step guide using the knowledge graph.

    Pipeline:
    1. Analyze issue → find matched files
    2. Identify entry-point files (APIs, routes, high-degree nodes)
    3. Trace dependencies via BFS through the graph
    4. Build logical investigation order
    5. LLM generates detailed, experience-tailored contribution steps

    Returns structured path with steps, files, actions, and setup commands.
    """
    try:
        owner, repo = parse_github_url(request.github_url)

        cache_key = (
            f"ai_path_{owner}_{repo}_{request.issue_number}"
            f"_{request.user_profile.experience}"
        )
        cached = get_cache(cache_key)
        if cached:
            return cached

        repo_data = await analyze_repo(
            owner, repo, request.user_profile.dict(),
        )

        # Find the target issue
        target_issue = None
        for issue in repo_data["issues"]:
            if issue.get("number") == request.issue_number:
                target_issue = issue
                break

        if not target_issue:
            issues = await fetch_issues(owner, repo)
            for issue in issues:
                if issue.get("number") == request.issue_number:
                    target_issue = issue
                    break

        if not target_issue:
            raise HTTPException(
                status_code=404,
                detail=f"Issue #{request.issue_number} not found in {owner}/{repo}",
            )

        # Build the knowledge graph
        graph = build_graph(
            repo_data["file_tree"],
            repo_data["file_contents"],
        )

        # Run the contribution path pipeline
        result = await generate_path(
            issue=target_issue,
            graph=graph,
            file_contents=repo_data["file_contents"],
            user_profile=request.user_profile.dict(),
        )

        result["repo"] = f"{owner}/{repo}"

        set_cache(cache_key, result)
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))