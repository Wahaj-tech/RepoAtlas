"""
Pre-filtering and scoring service for issue matching.
Runs fast algorithmic checks BEFORE sending to AI for final ranking.
"""

# Map file extensions to language names
EXT_TO_LANG = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".jsx": "javascript", ".tsx": "typescript", ".go": "go",
    ".java": "java", ".rb": "ruby", ".cpp": "c++", ".c": "c",
    ".rs": "rust", ".php": "php", ".swift": "swift", ".kt": "kotlin",
}

# Labels that signal difficulty
EASY_LABELS = {"good first issue", "beginner", "easy", "starter", "help wanted", "low-hanging fruit"}
MEDIUM_LABELS = {"enhancement", "feature", "improvement", "medium"}
HARD_LABELS = {"bug", "critical", "complex", "hard", "performance", "security"}

EXPERIENCE_WEIGHTS = {
    "beginner": {"easy": 1.0, "medium": 0.4, "hard": 0.1},
    "intermediate": {"easy": 0.6, "medium": 1.0, "hard": 0.5},
    "advanced": {"easy": 0.3, "medium": 0.7, "hard": 1.0},
}


def estimate_difficulty(labels: list[str]) -> str:
    label_set = {l.lower() for l in labels}
    if label_set & EASY_LABELS:
        return "easy"
    if label_set & HARD_LABELS:
        return "hard"
    if label_set & MEDIUM_LABELS:
        return "medium"
    return "medium"


def compute_language_overlap(issue_body: str, issue_labels: list[str],
                             repo_files: list[str], user_languages: list[str]) -> float:
    """Score 0-1 based on how well user's languages match the repo/issue."""
    user_langs = {l.lower() for l in user_languages}

    # Check if any label mentions a language the user knows
    label_langs = {l.lower() for l in issue_labels}
    label_match = bool(user_langs & label_langs)

    # Check repo file extensions
    repo_langs = set()
    for f in repo_files:
        ext = "." + f.rsplit(".", 1)[-1] if "." in f else ""
        lang = EXT_TO_LANG.get(ext)
        if lang:
            repo_langs.add(lang)

    overlap = user_langs & repo_langs
    repo_score = len(overlap) / max(len(repo_langs), 1)

    if label_match:
        return min(1.0, repo_score + 0.3)
    return repo_score


def score_issue(issue: dict, user_profile: dict, repo_files: list[str]) -> dict:
    """Compute a pre-filter score for a single issue."""
    labels = [l["name"] for l in issue.get("labels", [])]
    difficulty = estimate_difficulty(labels)
    experience = user_profile.get("experience", "beginner").lower()

    # Difficulty fit
    weights = EXPERIENCE_WEIGHTS.get(experience, EXPERIENCE_WEIGHTS["beginner"])
    diff_score = weights.get(difficulty, 0.5)

    # Language overlap
    lang_score = compute_language_overlap(
        issue.get("body", "") or "",
        labels,
        repo_files,
        user_profile.get("languages", []),
    )

    # Recency bonus — issues with fewer comments are less intimidating
    comments = issue.get("comments", 0)
    freshness = max(0, 1.0 - comments / 20)

    # Interest matching
    interest_score = 0.0
    interests = {i.lower() for i in (user_profile.get("interests") or [])}
    if interests:
        label_set = {l.lower() for l in labels}
        body_lower = (issue.get("body") or "").lower()
        for interest in interests:
            if interest in label_set or interest in body_lower:
                interest_score += 0.3
        interest_score = min(interest_score, 1.0)

    # Weighted total
    total = (
        diff_score * 0.35
        + lang_score * 0.30
        + freshness * 0.15
        + interest_score * 0.20
    )

    return {
        "issue": issue,
        "pre_score": round(total * 100),
        "difficulty": difficulty,
        "labels": labels,
    }


def prefilter_issues(issues: list[dict], user_profile: dict,
                     repo_files: list[str], max_candidates: int = 15,
                     label_filter: list[str] | None = None) -> list[dict]:
    """
    Score and rank issues, return top candidates for AI refinement.
    Automatically filters out pull requests.
    """
    # Reject pull requests — only open issues are valid contribution targets
    issues = [
        i for i in issues
        if not i.get("pull_request") and "/pull/" not in i.get("html_url", "")
    ]

    if label_filter:
        filter_set = {l.lower() for l in label_filter}
        issues = [
            i for i in issues
            if filter_set & {l["name"].lower() for l in i.get("labels", [])}
        ]

    scored = [score_issue(i, user_profile, repo_files) for i in issues]
    scored.sort(key=lambda x: x["pre_score"], reverse=True)
    return scored[:max_candidates]
