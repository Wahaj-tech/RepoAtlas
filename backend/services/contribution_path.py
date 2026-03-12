"""
Contribution Path Generator — Creates step-by-step guides using the knowledge graph.

Pipeline:
1. Identify entry-point files from issue matcher results
2. Trace dependencies through the graph (BFS/topological)
3. Build a logical investigation order
4. Use LLM to add context-aware descriptions for each step
"""

import networkx as nx
from services.llm_reasoner import generate_contribution_steps
from services.issue_matcher import analyze_issue


# ── Entry Point Detection ────────────────────────────────────────────────────

def find_entry_points(
    matched_files: list[dict],
    graph: nx.DiGraph,
    max_entries: int = 5,
) -> list[str]:
    """
    Identify the best entry-point files for investigation.

    Entry points are files that:
    - Score highly in issue matching
    - Have high in-degree (many files depend on them) — API/route files
    - Or are leaf nodes (no dependencies) — utility files
    """
    candidates = []

    for match in matched_files[:15]:
        filepath = match["file"]
        if filepath not in graph:
            continue

        in_deg = graph.in_degree(filepath)
        out_deg = graph.out_degree(filepath)
        score = match["score"]

        # Entry point heuristic:
        # High in-degree = many things import it (core file)
        # Zero out-degree = leaf/utility
        # Route/api/main in name = obvious entry
        is_api = any(
            kw in filepath.lower()
            for kw in ["api", "route", "view", "controller", "main", "app", "handler"]
        )

        entry_score = score
        if is_api:
            entry_score += 0.3
        if in_deg > 2:
            entry_score += 0.2
        if out_deg == 0:
            entry_score += 0.1

        candidates.append({
            "file": filepath,
            "entry_score": round(entry_score, 3),
            "in_degree": in_deg,
            "out_degree": out_deg,
        })

    candidates.sort(key=lambda x: x["entry_score"], reverse=True)
    return [c["file"] for c in candidates[:max_entries]]


# ── Dependency Chain Traversal ───────────────────────────────────────────────

def trace_dependency_chain(
    entry_points: list[str],
    graph: nx.DiGraph,
    max_depth: int = 5,
) -> list[dict]:
    """
    BFS from entry points through the dependency graph.
    Returns an ordered investigation chain with depth info.
    """
    visited = set()
    chain = []

    queue = [(ep, 0) for ep in entry_points]

    while queue:
        node, depth = queue.pop(0)

        if node in visited or depth > max_depth:
            continue
        visited.add(node)

        if node not in graph:
            continue

        # Gather node metadata
        node_data = graph.nodes.get(node, {})
        successors = list(graph.successors(node))
        predecessors = list(graph.predecessors(node))

        chain.append({
            "file": node,
            "depth": depth,
            "imports": successors[:10],
            "imported_by": predecessors[:10],
            "extension": node_data.get("extension", ""),
            "size": node_data.get("size", 0),
        })

        # Continue BFS through dependencies
        for succ in successors:
            if succ not in visited:
                queue.append((succ, depth + 1))

    return chain


# ── Investigation Order ─────────────────────────────────────────────────────

def build_investigation_order(
    entry_points: list[str],
    dependency_chain: list[dict],
    matched_files: list[dict],
) -> list[dict]:
    """
    Build a logical investigation order combining:
    - Entry points first
    - Then dependency chain by depth
    - Annotated with relevance scores from matching
    """
    # Build score lookup
    score_map = {m["file"]: m["score"] for m in matched_files}

    order = []
    seen = set()
    step = 1

    # Entry points first
    for ep in entry_points:
        if ep not in seen:
            seen.add(ep)
            chain_info = next((c for c in dependency_chain if c["file"] == ep), {})
            order.append({
                "step": step,
                "file": ep,
                "role": "entry_point",
                "relevance_score": score_map.get(ep, 0),
                "imports": chain_info.get("imports", []),
                "imported_by": chain_info.get("imported_by", []),
            })
            step += 1

    # Then dependencies in BFS order
    for item in dependency_chain:
        if item["file"] not in seen:
            seen.add(item["file"])
            order.append({
                "step": step,
                "file": item["file"],
                "role": "dependency" if item["depth"] > 0 else "entry_point",
                "relevance_score": score_map.get(item["file"], 0),
                "imports": item.get("imports", []),
                "imported_by": item.get("imported_by", []),
            })
            step += 1

    return order


# ── Main Pipeline ────────────────────────────────────────────────────────────

async def generate_path(
    issue: dict,
    graph: nx.DiGraph,
    file_contents: dict[str, str],
    user_profile: dict,
) -> dict:
    """
    Full contribution path generation pipeline:
    1. Run issue matcher to find relevant files
    2. Identify entry points
    3. Trace dependency chain
    4. Build investigation order
    5. Send to LLM for step-by-step guide with explanations

    Returns structured JSON ready for frontend rendering.
    """
    issue_title = issue.get("title", "")
    issue_body = issue.get("body") or ""
    issue_labels = [l["name"] for l in issue.get("labels", [])]

    # Step 1 — Analyze the issue to find matched files
    analysis = await analyze_issue(
        issue_title=issue_title,
        issue_body=issue_body,
        issue_labels=issue_labels,
        graph=graph,
        file_contents=file_contents,
        use_llm=False,  # algorithmic only for speed; LLM adds steps below
    )

    matched_files = analysis.get("matched_files", [])

    if not matched_files:
        # Fallback: use all files with some degree
        matched_files = [
            {"file": n, "score": graph.degree(n) / max(1, max(graph.degree(nd) for nd in graph.nodes) or 1)}
            for n in graph.nodes
            if graph.degree(n) > 0
        ]
        matched_files.sort(key=lambda x: x["score"], reverse=True)
        matched_files = matched_files[:10]

    # Step 2 — Find entry points
    entry_points = find_entry_points(matched_files, graph)

    # Step 3 — Trace dependencies
    dependency_chain = trace_dependency_chain(entry_points, graph)

    # Step 4 — Build investigation order
    investigation_order = build_investigation_order(
        entry_points, dependency_chain, matched_files
    )

    # Step 5 — LLM generates the user-facing contribution guide
    experience = user_profile.get("experience", "beginner")
    languages = user_profile.get("languages", [])

    llm_result = await generate_contribution_steps(
        issue_title=issue_title,
        issue_body=issue_body,
        issue_labels=issue_labels,
        entry_files=entry_points,
        dependency_chain=investigation_order,
        experience=experience,
        languages=languages,
    )

    return {
        "issue": {
            "number": issue.get("number"),
            "title": issue_title,
            "url": issue.get("html_url", ""),
            "labels": issue_labels,
        },
        "analysis": {
            "keywords": analysis.get("keywords_extracted", []),
            "entry_points": entry_points,
            "files_analyzed": len(matched_files),
        },
        "contribution_path": llm_result.get("contribution_path", []),
        "estimated_time": llm_result.get("estimated_time", "unknown"),
        "key_files": llm_result.get("key_files", entry_points),
        "tips": llm_result.get("tips", ""),
        "setup_commands": llm_result.get("setup_commands", []),
        "testing_strategy": llm_result.get("testing_strategy", ""),
    }
