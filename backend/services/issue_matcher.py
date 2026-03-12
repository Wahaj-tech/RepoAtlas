"""
Issue Matching Engine — Maps GitHub issues to relevant codebase files.

Pipeline:
1. Extract keywords from issue title + body + labels
2. Match keywords against file names, classes, functions in the graph
3. Expand matches through the knowledge graph (neighbors, dependencies)
4. Score and rank files by relevance
5. Send top candidates to the LLM for refined scoring + difficulty estimate
"""

import re
import networkx as nx
from services.llm_reasoner import analyze_issue_relevance


# ── Keyword Extraction ──────────────────────────────────────────────────────

# Common words to ignore when extracting keywords
_STOP_WORDS = {
    "the", "is", "at", "which", "on", "a", "an", "and", "or", "but", "in",
    "to", "for", "of", "with", "it", "this", "that", "be", "as", "are",
    "was", "were", "been", "has", "have", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "can", "not", "no", "when",
    "if", "we", "i", "you", "they", "he", "she", "my", "our", "your",
    "from", "by", "about", "into", "through", "after", "before", "between",
    "out", "up", "down", "all", "each", "every", "both", "few", "more",
    "some", "any", "how", "what", "where", "who", "why", "so", "than",
    "too", "very", "just", "also", "now", "here", "there", "then", "only",
    "new", "one", "two", "first", "last", "see", "get", "set", "use",
    "add", "try", "fix", "make", "need", "want", "like", "way", "time",
}


def extract_keywords(title: str, body: str, labels: list[str]) -> list[str]:
    """
    Extract meaningful keywords from issue text.
    Returns de-duplicated list sorted by likely importance.
    """
    text = f"{title} {title} {' '.join(labels)} {body or ''}"  # title weighted 2x
    # Split on non-alphanumeric (keep underscores for identifiers)
    tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', text.lower())
    # Filter stop words and very short tokens
    keywords = [t for t in tokens if t not in _STOP_WORDS and len(t) > 2]
    # De-duplicate preserving order
    seen = set()
    unique = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)
    return unique


# ── File Matching ────────────────────────────────────────────────────────────

def _file_keyword_score(filepath: str, keywords: list[str]) -> float:
    """Score a file path against keywords (0.0 - 1.0)."""
    fp_lower = filepath.lower().replace("/", " ").replace("\\", " ").replace(".", " ")
    fp_parts = set(fp_lower.split())
    # Also check the full path as a string
    hits = 0
    for kw in keywords:
        if kw in fp_parts or kw in fp_lower:
            hits += 1
    return hits / max(len(keywords), 1)


def _content_keyword_score(content: str, keywords: list[str]) -> float:
    """Score file content against keywords (0.0 - 1.0)."""
    if not content:
        return 0.0
    content_lower = content.lower()
    hits = sum(1 for kw in keywords if kw in content_lower)
    return hits / max(len(keywords), 1)


def match_files_to_issue(
    keywords: list[str],
    graph: nx.DiGraph,
    file_contents: dict[str, str],
) -> list[dict]:
    """
    Match keywords against every file in the graph.
    Returns list of {file, score, match_type} sorted by score desc.
    """
    scores = {}

    for node in graph.nodes:
        # Path-based matching (higher weight — file names are strong signals)
        path_score = _file_keyword_score(node, keywords)

        # Content-based matching
        content = file_contents.get(node, "")
        content_score = _content_keyword_score(content, keywords)

        combined = path_score * 0.6 + content_score * 0.4

        if combined > 0.0:
            match_type = "path+content" if path_score > 0 and content_score > 0 \
                else "path" if path_score > 0 else "content"
            scores[node] = {"score": round(combined, 3), "match_type": match_type}

    ranked = sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True)
    return [
        {"file": f, "score": info["score"], "match_type": info["match_type"]}
        for f, info in ranked
    ]


# ── Graph Expansion ─────────────────────────────────────────────────────────

def expand_with_graph(
    matched_files: list[dict],
    graph: nx.DiGraph,
    max_expand: int = 10,
) -> list[dict]:
    """
    Expand matched files with their graph neighbors.
    Files that are imported by or import matched files get a derived score.
    """
    existing = {m["file"] for m in matched_files}
    expanded = list(matched_files)

    for match in matched_files[:max_expand]:
        node = match["file"]
        if node not in graph:
            continue

        # Successors = files this file imports
        for succ in graph.successors(node):
            if succ not in existing:
                expanded.append({
                    "file": succ,
                    "score": round(match["score"] * 0.6, 3),
                    "match_type": "graph_dependency",
                })
                existing.add(succ)

        # Predecessors = files that import this file
        for pred in graph.predecessors(node):
            if pred not in existing:
                expanded.append({
                    "file": pred,
                    "score": round(match["score"] * 0.5, 3),
                    "match_type": "graph_dependent",
                })
                existing.add(pred)

    # Re-sort by score
    expanded.sort(key=lambda x: x["score"], reverse=True)
    return expanded


# ── Centrality Boost ─────────────────────────────────────────────────────────

def apply_centrality_boost(
    matched_files: list[dict],
    graph: nx.DiGraph,
) -> list[dict]:
    """
    Boost scores of files that are central in the dependency graph.
    High-degree files are more likely to be important modification points.
    """
    if not graph.nodes:
        return matched_files

    max_degree = max(graph.degree(n) for n in graph.nodes) or 1

    for match in matched_files:
        node = match["file"]
        if node in graph:
            centrality = graph.degree(node) / max_degree
            # Blend: 85% keyword score + 15% centrality
            match["score"] = round(match["score"] * 0.85 + centrality * 0.15, 3)
            match["centrality"] = round(centrality, 3)

    matched_files.sort(key=lambda x: x["score"], reverse=True)
    return matched_files


# ── Main Pipeline ────────────────────────────────────────────────────────────

async def analyze_issue(
    issue_title: str,
    issue_body: str,
    issue_labels: list[str],
    graph: nx.DiGraph,
    file_contents: dict[str, str],
    use_llm: bool = True,
) -> dict:
    """
    Full issue analysis pipeline:
    1. Extract keywords
    2. Match files by keyword
    3. Expand via graph
    4. Apply centrality boost
    5. (Optional) Refine with LLM

    Returns structured JSON with matched_files, difficulty, estimated_time.
    """
    # Step 1 — Keywords
    keywords = extract_keywords(issue_title, issue_body, issue_labels)

    # Step 2 — Keyword matching
    matched = match_files_to_issue(keywords, graph, file_contents)

    if not matched:
        return {
            "issue": issue_title,
            "keywords_extracted": keywords,
            "matched_files": [],
            "difficulty": "unknown",
            "estimated_time": "unknown",
            "reasoning": "No files matched the issue keywords.",
        }

    # Step 3 — Graph expansion
    expanded = expand_with_graph(matched, graph)

    # Step 4 — Centrality boost
    scored = apply_centrality_boost(expanded, graph)

    # Take top 15 for LLM refinement
    top_candidates = scored[:15]

    # Step 5 — LLM refinement (optional, requires API key)
    if use_llm:
        graph_context = [n for n in graph.nodes]
        llm_result = await analyze_issue_relevance(
            issue_title=issue_title,
            issue_body=issue_body,
            issue_labels=issue_labels,
            matched_files=top_candidates,
            graph_context=graph_context,
        )
        llm_result["keywords_extracted"] = keywords
        llm_result["issue"] = issue_title
        return llm_result

    # Without LLM — return algorithmic results only
    return {
        "issue": issue_title,
        "keywords_extracted": keywords,
        "matched_files": top_candidates[:10],
        "difficulty": _estimate_difficulty_from_labels(issue_labels),
        "estimated_time": "unknown (LLM not used)",
        "reasoning": "Algorithmic matching only — no LLM refinement.",
    }


def _estimate_difficulty_from_labels(labels: list[str]) -> str:
    """Simple label-based difficulty estimation."""
    label_set = {l.lower() for l in labels}
    easy = {"good first issue", "beginner", "easy", "starter", "help wanted"}
    hard = {"bug", "critical", "complex", "hard", "performance", "security"}
    if label_set & easy:
        return "easy"
    if label_set & hard:
        return "hard"
    return "medium"
