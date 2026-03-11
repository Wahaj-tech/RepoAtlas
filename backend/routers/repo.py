from fastapi import APIRouter, HTTPException
from models.schemas import AnalyzeRequest, ImpactRequest
from services.analyzer_service import analyze_repo
from services.graph_service import build_graph, get_impact, export_graph
from services.cache_service import get_cache, set_cache
from services.ai_service import get_recommendations

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