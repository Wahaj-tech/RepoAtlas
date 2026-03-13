from groq import Groq
import json
import os
from dotenv import load_dotenv
from services.matching_service import prefilter_issues

load_dotenv()

_client = None


def get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set. Add it to backend/.env")
        _client = Groq(api_key=api_key)
    return _client


def _parse_ai_json(raw: str):
    """Strip markdown fences and parse JSON from AI response."""
    clean = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(clean)


def _label_based_fallback(issues, max_results=3):
  """
  Fallback issue selection when Groq is unavailable/rate-limited.
  Uses raw fetched issues, filters by useful starter labels, sorts by recency.
  """
  allowed_terms = ["bug", "good first issue", "documentation", "enhancement"]

  filtered = []
  for issue in issues:
    if issue.get("pull_request"):
      continue
    labels = [l.get("name", "") for l in issue.get("labels", [])]
    labels_lower = [l.lower() for l in labels]
    if any(any(term in lbl for term in allowed_terms) for lbl in labels_lower):
      filtered.append((issue, labels))

  filtered.sort(
    key=lambda x: x[0].get("updated_at") or "",
    reverse=True,
  )

  if not filtered:
    non_pr = []
    for issue in issues:
      if issue.get("pull_request"):
        continue
      labels = [l.get("name", "") for l in issue.get("labels", [])]
      non_pr.append((issue, labels))
    non_pr.sort(key=lambda x: x[0].get("updated_at") or "", reverse=True)
    filtered = non_pr

  return [
    {
      "issue_id": issue.get("number"),
      "title": issue.get("title", "Untitled issue"),
      "match_score": 70,
      "difficulty": "medium",
      "why_good_match": "Good starter issue based on labels",
      "files_to_look_at": [],
      "estimated_time": "2-4 hours",
      "labels": labels,
      "url": issue.get("html_url", ""),
    }
    for issue, labels in filtered[:max_results]
  ]


def _estimate_time_from_difficulty(difficulty: str, experience: str) -> str:
  difficulty = (difficulty or "medium").lower()
  experience = (experience or "beginner").lower()

  table = {
    "beginner": {"easy": "2-4 hours", "medium": "1-2 days", "hard": "3-5 days"},
    "intermediate": {"easy": "1-3 hours", "medium": "4-8 hours", "hard": "2-3 days"},
    "advanced": {"easy": "1-2 hours", "medium": "2-6 hours", "hard": "1-2 days"},
  }
  return table.get(experience, table["beginner"]).get(difficulty, "4-8 hours")


def _fallback_ranked_issues(candidates, user_profile, max_results=3, include_url=False):
  """Deterministic fallback ranking when AI is unavailable/rate-limited."""
  out = []
  experience = user_profile.get("experience", "beginner")

  for c in candidates[:max_results]:
    issue = c["issue"]
    labels = c.get("labels", [])
    difficulty = c.get("difficulty", "medium")
    pre_score = int(c.get("pre_score", 50))

    result = {
      "issue_id": issue.get("number"),
      "title": issue.get("title", "Untitled issue"),
      "why_good_match": (
        "Matched using language overlap, issue labels, and scope fit for your profile. "
        "Review the issue discussion and linked files to confirm implementation details."
      ),
      "difficulty": difficulty,
      "files_to_look_at": [],
      "estimated_time": _estimate_time_from_difficulty(difficulty, experience),
      "match_score": max(35, min(99, pre_score)),
    }

    if include_url:
      result["labels"] = labels
      result["url"] = issue.get("html_url", "")

    out.append(result)

  return out


async def get_recommendations(issues, graph, user_profile):
    """Recommendation function used by /api/analyze."""
    repo_files = [n["id"] for n in graph["nodes"]]
    candidates = prefilter_issues(issues, user_profile, repo_files, max_candidates=15)

    if not candidates:
      fallback = _label_based_fallback(issues, max_results=3)
      return [
        {
          "issue_id": i["issue_id"],
          "title": i["title"],
          "why_good_match": i["why_good_match"],
          "difficulty": i["difficulty"],
          "files_to_look_at": i["files_to_look_at"],
          "estimated_time": i["estimated_time"],
          "match_score": i["match_score"],
        }
        for i in fallback
      ]

    issues_for_ai = [
        {
            "id": c["issue"]["number"],
            "title": c["issue"]["title"],
            "labels": c["labels"],
            "pre_score": c["pre_score"],
            "difficulty": c["difficulty"],
        }
        for c in candidates
    ]

    prompt = f"""You are RepoAtlas AI — a senior open-source framework maintainer,
software architect, and expert debugging mentor.

Your mission is to maximize the probability that a developer
successfully completes a real contribution in a complex repository.

You must think in terms of:
- architectural risk
- execution flow reasoning
- dependency impact
- contributor confidence building

==================================================
CRITICAL PRODUCT RULE
==================================================
Never recommend or generate contribution guidance
for Pull Requests.

Only open unresolved issues are valid contribution targets.

If an issue appears to be a PR — internally reject it
and prefer another issue.

==================================================
USER PROFILE
==================================================
Languages: {user_profile.get('languages')}
Experience: {user_profile.get('experience')}
Time Available: {user_profile.get('time_available')}
Interests: {user_profile.get('interests', 'not specified')}

==================================================
REPOSITORY INTELLIGENCE
==================================================
Repo files: {repo_files[:40]}

Pre-scored candidate issues:
{json.dumps(issues_for_ai, indent=2)}

==================================================
TASK: ISSUE MATCHING
==================================================
Select the TOP 3 issues that are the best match.

Recommend issues that balance:
- learning value
- architectural safety
- scope clarity
- success probability

Difficulty classification must consider subsystem criticality.

Core framework subsystems automatically increase difficulty:
  routing engine, session lifecycle, request context,
  middleware dispatch, async runtime, security/auth layer

Beginner developers should rarely be guided toward
core lifecycle refactors.

For EACH selected issue return:

1. why_good_match
   - MUST be specific
   - Mention exact subsystem name
   - Why scope is contained or risky
   - Which file acts as investigation entry point
   - Expected conceptual takeaway

2. difficulty (easy / medium / hard)
   EASY: small bug, docs, config change, single file
   MEDIUM: feature tweak, limited refactor, 2-4 files
   HARD: core architecture, routing, concurrency, security, large refactor

3. files_to_look_at — max 3 real file paths

4. estimated_time — based on experience + subsystem depth

5. match_score (0-100)
   Higher: strong language match, small scope, interest alignment
   Lower: architectural risk, vague description, many modules
   Scores must show real spread (e.g. 92 vs 61).

==================================================
SELF REVIEW BEFORE OUTPUT
==================================================
- Is this accidentally a pull request?
- Are filenames realistic and minimal?
- Is architectural risk honestly communicated?
- Is estimated time believable?
- Do scores vary meaningfully?

Return ONLY valid JSON array, no explanation, no markdown backticks:
[
  {{
    "issue_id": 123,
    "title": "issue title",
    "why_good_match": "specific reasoning with subsystem + entry file",
    "difficulty": "easy",
    "files_to_look_at": ["file1.py"],
    "estimated_time": "1-2 hours",
    "match_score": 95
  }}
]"""

    try:
      response = get_client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1200,
        temperature=0.3,
      )
      return _parse_ai_json(response.choices[0].message.content)
    except Exception as e:
      print(f"GROQ ERROR IN GET_RECOMMENDATIONS: {type(e).__name__}: {e}")
      fallback = _label_based_fallback(issues, max_results=3)
      # get_recommendations schema doesn't require labels/url, keep only required fields.
      return [
        {
          "issue_id": i["issue_id"],
          "title": i["title"],
          "why_good_match": i["why_good_match"],
          "difficulty": i["difficulty"],
          "files_to_look_at": i["files_to_look_at"],
          "estimated_time": i["estimated_time"],
          "match_score": i["match_score"],
        }
        for i in fallback
      ]


async def match_issues(issues, graph, user_profile, max_results=5, label_filter=None):
    """
    Enhanced issue matching: algorithmic pre-filter then AI ranking.
    Returns scored and explained matches.
    """
    repo_files = [n["id"] for n in graph["nodes"]]
    candidates = prefilter_issues(
        issues, user_profile, repo_files,
        max_candidates=max(max_results * 3, 15),
        label_filter=label_filter,
    )

    if not candidates:
      return _label_based_fallback(issues, max_results=3)

    issues_for_ai = [
        {
            "id": c["issue"]["number"],
            "title": c["issue"]["title"],
            "labels": c["labels"],
            "pre_score": c["pre_score"],
            "difficulty": c["difficulty"],
            "url": c["issue"].get("html_url", ""),
        }
        for c in candidates
    ]

    prompt = f"""You are RepoAtlas AI — a senior open-source framework maintainer,
software architect, and expert debugging mentor.

Your mission is to maximize the probability that a developer
successfully completes a real contribution in a complex repository.

==================================================
CRITICAL PRODUCT RULE
==================================================
Never recommend Pull Requests. Only open unresolved issues.
If an issue appears to be a PR — reject it and prefer another.

==================================================
USER PROFILE
==================================================
Languages: {user_profile.get('languages')}
Experience: {user_profile.get('experience')}
Time Available: {user_profile.get('time_available')}
Interests: {user_profile.get('interests', 'not specified')}

==================================================
REPOSITORY INTELLIGENCE
==================================================
Repo files: {repo_files[:50]}

Candidate issues (pre-filtered):
{json.dumps(issues_for_ai, indent=2)}

==================================================
CRITICAL REQUIREMENT
==================================================
User knows these languages: {user_profile.get('languages', [])}

You MUST only recommend issues that involve
these specific languages.

If the repo is Python but user selected JavaScript,
look for issues that involve:
- JavaScript/TypeScript files in the repo
- Documentation issues (language agnostic)
- Configuration issues (language agnostic)
- Build/tooling issues

If NO issues match the user's languages at all,
return issues labeled as "documentation" or
"good first issue" that don't require language
specific knowledge.

NEVER return issues that require knowledge of
a language the user did NOT select.

==================================================
TASK: ISSUE MATCHING
==================================================
Select the TOP {max_results} issues that are the best match.

Recommend issues that balance:
- learning value
- architectural safety
- scope clarity
- success probability

Core framework subsystems automatically increase difficulty:
  routing engine, session lifecycle, request context,
  middleware dispatch, async runtime, security/auth layer

Beginner developers should rarely be guided toward
core lifecycle refactors.

For EACH selected issue return:

1. why_good_match — specific: subsystem name, entry point file, scope risk, conceptual takeaway
2. difficulty (easy / medium / hard) — consider subsystem criticality
3. files_to_look_at — max 3 real file paths
4. estimated_time — based on experience + subsystem depth
5. match_score (0-100) — scores must show real spread (e.g. 92 vs 61)

==================================================
SELF REVIEW
==================================================
- Is this a PR? Reject.
- Are filenames realistic?
- Is architectural risk honestly communicated?
- Is estimated time believable?

Return ONLY valid JSON array, no explanation, no markdown backticks:
[
  {{
    "issue_id": 123,
    "title": "issue title",
    "why_good_match": "specific reasoning with subsystem + entry file",
    "difficulty": "easy",
    "files_to_look_at": ["file1.py"],
    "estimated_time": "1-2 hours",
    "match_score": 92,
    "labels": ["good first issue"],
    "url": "https://github.com/..."
  }}
]"""

    try:
      response = get_client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
        temperature=0.3,
      )
      return _parse_ai_json(response.choices[0].message.content)
    except Exception as e:
      print(f"GROQ ERROR IN MATCH_ISSUES: {type(e).__name__}: {e}")
      return _label_based_fallback(issues, max_results=3)


async def get_contribution_path(issue, graph, user_profile):
    """Generate a step-by-step contribution guide for a specific issue."""
    repo_files = [n["id"] for n in graph["nodes"]]
    experience = user_profile.get("experience", "beginner")
    languages = user_profile.get("languages", [])

    # Find files related to this issue via import graph edges
    edges = graph.get("edges", [])
    connected_files = set()
    for e in edges[:100]:
        connected_files.add(e["source"])
        connected_files.add(e["target"])

    issue_title = issue.get('title', '')
    issue_body = (issue.get('body') or '')[:500]
    issue_labels = [l['name'] for l in issue.get('labels', [])]

    prompt = f"""You are RepoAtlas AI — a senior open-source framework maintainer,
software architect, and expert debugging mentor.

Your mission is to generate a HIGHLY PRACTICAL step-by-step
technical contribution roadmap for solving a specific issue.

You must think in terms of:
- architectural risk
- execution flow reasoning
- dependency impact
- contributor confidence building

==================================================
CRITICAL RULE
==================================================
Never generate guidance for Pull Requests.
Only open unresolved issues are valid targets.

==================================================
USER PROFILE
==================================================
Languages: {languages}
Experience: {experience}
Time Available: {user_profile.get('time_available', 'not specified')}
Interests: {user_profile.get('interests', 'not specified')}

==================================================
ISSUE CONTEXT
==================================================
Issue Title: {issue_title}
Issue Summary: {issue_body}
Labels: {issue_labels}
Likely Files: {repo_files[:50]}
Connected Files (import graph): {list(connected_files)[:30]}

==================================================
TASK: CONTRIBUTION ROADMAP
==================================================
Generate a REAL engineering investigation workflow.
Do NOT include Git workflow basics (fork/clone/PR).

Guide the developer through:

1. Entry-point discovery
   → identify first file to open
   → identify function/class to search

2. Execution path tracing
   → follow request or lifecycle flow
   → inspect object creation or dispatch logic

3. Architectural understanding
   → explain subsystem responsibility briefly

4. Refactor strategy thinking
   → where abstraction boundary likely exists
   → where duplication or coupling risk exists

5. Side-effect awareness
   → what behavior could silently break

6. Intelligent validation
   → specific tests OR runtime scenario
   → observable signals of correctness

Adapt depth based on experience:
  BEGINNER: more explanation, smaller chunks, debugging hints
  INTERMEDIATE: faster conceptual jumps, design focus
  ADVANCED: architecture reasoning, edge-case thinking

==================================================
TIME ESTIMATION
==================================================
Consider dependency depth and subsystem criticality.
Framework core refactors are NEVER quick beginner fixes.

==================================================
SELF REVIEW
==================================================
- Are steps specific to THIS issue?
- Would this actually help someone fix it?
- Is architectural risk honestly communicated?
- Are steps free from generic Git workflow noise?

Return ONLY valid JSON, no explanation, no markdown backticks:
{{
  "steps": [
    {{
      "step": 1,
      "title": "technical objective",
      "action": "precise developer action",
      "file": "path/to/file.py",
      "why": "engineering reasoning"
    }}
  ],
  "estimated_total_time": "realistic duration",
  "key_files": ["file1.py", "file2.py"],
  "tips": "one deep insight for this issue",
  "setup_commands": []
}}"""

    response = get_client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
        temperature=0.3,
    )
    return _parse_ai_json(response.choices[0].message.content)