import httpx
import time
from fastapi import APIRouter, HTTPException
from models.schemas import (
    AnalyzeRequest, ImpactRequest,
    MatchIssuesRequest, ContributionPathRequest,
    AnalyzeIssueRequest, GeneratePathRequest,
)
from services.analyzer_service import analyze_repo
from services.graph_service import build_graph, get_impact, export_graph, get_graph_for_repo
from services.cache_service import get_cache, set_cache
from services.ai_service import get_recommendations, match_issues, get_contribution_path
from services.github_service import fetch_issues, fetch_repo_metadata, fetch_repo_languages
from services.issue_matcher import analyze_issue
from services.contribution_path import generate_path

router = APIRouter()


def clean_github_url(url: str) -> str:
    url = url.strip()
    url = url.rstrip("/")
    url = url.replace(".git", "")
    return url

def parse_github_url(url: str):
    parts = clean_github_url(url).split("/")
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")
    return parts[-2], parts[-1]


@router.get("/repo-languages")
async def get_repo_languages(github_url: str):
    try:
        github_url = clean_github_url(github_url)
        owner, repo = parse_github_url(github_url)

        async with httpx.AsyncClient() as client:
            languages = await fetch_repo_languages(owner, repo, client)

        return {
            "languages": languages,
            "primary": languages[0] if languages else "Unknown",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze")
async def analyze(request: AnalyzeRequest):
    try:
        owner, repo = parse_github_url(request.github_url)
        lang_str = "_".join(sorted(request.user_profile.languages or []))
        cache_key = f"{owner}_{repo}_{lang_str}_{request.user_profile.experience}"
        cached = get_cache(cache_key)
        if cached:
            if cached.get("recommendations") or cached.get("language_mismatch"):
                return cached
            print(f"[Analyze] Ignoring stale empty cached recommendations for {owner}/{repo}")
        repo_data = await analyze_repo(owner, repo, request.user_profile.dict())

        # Detect language mismatch.
        repo_primary_language = repo_data["metadata"].get("language", "")
        user_languages = request.user_profile.languages or []

        language_mismatch = False
        mismatch_message = None

        if repo_primary_language and user_languages:
            repo_lang_lower = repo_primary_language.lower()
            user_langs_lower = [l.lower() for l in user_languages]

            if repo_lang_lower not in user_langs_lower:
                language_mismatch = True
                mismatch_message = (
                    f"This repo is primarily {repo_primary_language}. "
                    f"Showing issues relevant to {', '.join(user_languages)} "
                    f"where possible, plus documentation issues."
                )

        repo_key = f"{owner}/{repo}"
        graph_start = time.perf_counter()
        graph = build_graph(repo_data["file_tree"], repo_data["file_contents"], repo_key=repo_key)
        graph_json = export_graph(graph)
        print(f"[Timing] Graph building time: {time.perf_counter() - graph_start:.2f}s")

        try:
            ai_start = time.perf_counter()
            recommendations = await get_recommendations(
                repo_data["issues"],
                graph_json,
                request.user_profile.dict(),
            )
            print(f"[Timing] AI recommendations time: {time.perf_counter() - ai_start:.2f}s")
        except Exception as rec_err:
            print(f"[Analyze] Recommendations fallback for {owner}/{repo}: {rec_err}")
            recommendations = []

        result = {
            "metadata": {"name": repo_data["metadata"].get("name"), "description": repo_data["metadata"].get("description"), "stars": repo_data["metadata"].get("stargazers_count"), "language": repo_data["metadata"].get("language")},
            "graph": graph_json,
            "recommendations": recommendations,
            "issues": repo_data["issues"][:10],
            "language_mismatch": language_mismatch,
            "mismatch_message": mismatch_message,
        }
        set_cache(cache_key, result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/match-issues")
async def match_issues_endpoint(request: MatchIssuesRequest):
    try:
        owner, repo = parse_github_url(request.github_url)
        label_key = "_".join(sorted(request.label_filter or []))
        lang_str = "_".join(sorted(request.user_profile.languages or []))
        cache_key = f"match_{owner}_{repo}_{lang_str}_{request.user_profile.experience}_{label_key}"
        cached = get_cache(cache_key)
        if cached:
            return cached
        repo_data = await analyze_repo(owner, repo, request.user_profile.dict())
        repo_key = f"{owner}/{repo}"
        graph = build_graph(repo_data["file_tree"], repo_data["file_contents"], repo_key=repo_key)
        graph_json = export_graph(graph)
        try:
            matches = await match_issues(
                repo_data["issues"],
                graph_json,
                request.user_profile.dict(),
                max_results=request.max_results,
                label_filter=request.label_filter,
            )
        except Exception as match_err:
            print(f"[MatchIssues] Falling back to empty matches for {owner}/{repo}: {match_err}")
            matches = []

        result = {"matches": matches, "total_issues_scanned": len(repo_data["issues"]), "repo": f"{owner}/{repo}"}
        set_cache(cache_key, result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/contribution-path")
async def contribution_path_endpoint(request: ContributionPathRequest):
    try:
        owner, repo = parse_github_url(request.github_url)
        lang_str = "_".join(sorted(request.user_profile.languages or []))
        cache_key = f"path_{owner}_{repo}_{request.issue_number}_{lang_str}_{request.user_profile.experience}"
        cached = get_cache(cache_key)
        if cached:
            return cached
        repo_data = await analyze_repo(owner, repo, request.user_profile.dict())
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
            raise HTTPException(status_code=404, detail=f"Issue #{request.issue_number} not found in {owner}/{repo}")
        repo_key = f"{owner}/{repo}"
        graph = build_graph(repo_data["file_tree"], repo_data["file_contents"], repo_key=repo_key)
        graph_json = export_graph(graph)
        path = await get_contribution_path(target_issue, graph_json, request.user_profile.dict())
        result = {
            "issue": {"number": target_issue.get("number"), "title": target_issue.get("title"), "url": target_issue.get("html_url"), "labels": [l["name"] for l in target_issue.get("labels", [])]},
            "contribution_path": path,
            "repo": f"{owner}/{repo}",
        }
        set_cache(cache_key, result)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/impact")
async def impact_endpoint(request: ImpactRequest):
    try:
        owner, repo = parse_github_url(request.github_url)
        repo_key = f"{owner}/{repo}"
        cache_key = f"impact_{owner}_{repo}_{request.file_path}"
        cached = get_cache(cache_key)
        if cached:
            return cached
        graph = get_graph_for_repo(repo_key)
        if graph is None:
            print(f"[Impact] Graph not found for {repo_key}, rebuilding...")
            repo_data = await analyze_repo(owner, repo, {})
            graph = build_graph(repo_data["file_tree"], repo_data["file_contents"], repo_key=repo_key)
        else:
            print(f"[Impact] Reusing cached graph for {repo_key} ({len(graph.nodes)} nodes)")
        result = get_impact(graph, request.file_path)
        result["file_path"] = request.file_path
        result["repo"] = f"{owner}/{repo}"
        set_cache(cache_key, result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze-issue")
async def analyze_issue_endpoint(request: AnalyzeIssueRequest):
    try:
        owner, repo = parse_github_url(request.github_url)
        cache_key = f"ai_issue_{owner}_{repo}_{request.issue_number}"
        cached = get_cache(cache_key)
        if cached:
            return cached
        repo_data = await analyze_repo(owner, repo, {})
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
            raise HTTPException(status_code=404, detail=f"Issue #{request.issue_number} not found in {owner}/{repo}")
        repo_key = f"{owner}/{repo}"
        graph = build_graph(repo_data["file_tree"], repo_data["file_contents"], repo_key=repo_key)
        issue_labels = [l["name"] for l in target_issue.get("labels", [])]
        result = await analyze_issue(issue_title=target_issue.get("title", ""), issue_body=target_issue.get("body") or "", issue_labels=issue_labels, graph=graph, file_contents=repo_data["file_contents"])
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
    try:
        owner, repo = parse_github_url(request.github_url)
        cache_key = f"ai_path_{owner}_{repo}_{request.issue_number}_{request.user_profile.experience}"
        cached = get_cache(cache_key)
        if cached:
            return cached
        repo_data = await analyze_repo(owner, repo, request.user_profile.dict())
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
            raise HTTPException(status_code=404, detail=f"Issue #{request.issue_number} not found in {owner}/{repo}")
        repo_key = f"{owner}/{repo}"
        graph = build_graph(repo_data["file_tree"], repo_data["file_contents"], repo_key=repo_key)
        result = await generate_path(issue=target_issue, graph=graph, file_contents=repo_data["file_contents"], user_profile=request.user_profile.dict())
        result["repo"] = f"{owner}/{repo}"
        set_cache(cache_key, result)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
