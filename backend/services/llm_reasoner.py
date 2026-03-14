"""
LLM Reasoner — Abstraction layer for all AI reasoning in RepoAtlas.

Handles prompt construction, API calls, and response parsing.
All LLM interactions go through this module so the model/provider
can be swapped without touching business logic.
"""

try:
  from groq import Groq
  _groq_import_error = None
except Exception as import_error:
  Groq = None
  _groq_import_error = import_error
import json
import os
from dotenv import load_dotenv

load_dotenv()

_client = None
MODEL = "llama-3.3-70b-versatile"


def _get_client():
  global _client
  if _client is None:
    if Groq is None:
      raise RuntimeError(
        "groq package is not installed. Add 'groq' to backend/requirements.txt"
      ) from _groq_import_error
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
      raise RuntimeError("GROQ_API_KEY is not set. Add it to backend/.env")
    _client = Groq(api_key=api_key)
  return _client


def _parse_json(raw: str):
    """Strip markdown fences and parse JSON from LLM output."""
    clean = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(clean)


async def reason(prompt: str, *, max_tokens: int = 1500, temperature: float = 0.3):
    """Send a prompt to the LLM and return parsed JSON."""
    response = _get_client().chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return _parse_json(response.choices[0].message.content)


async def analyze_issue_relevance(
    issue_title: str,
    issue_body: str,
    issue_labels: list[str],
    matched_files: list[dict],
    graph_context: list[str],
) -> dict:
    """Ask the LLM to refine file-to-issue relevance scores and estimate difficulty."""
    prompt = f"""You are RepoAtlas AI — a senior open-source framework maintainer
and expert code analyst.

Given a GitHub issue and candidate files matched via keyword + graph analysis,
refine the relevance scores and estimate difficulty.

==================================================
CRITICAL RULE
==================================================
If this issue is actually a Pull Request, return empty matched_files
and difficulty "unknown".

==================================================
ISSUE
==================================================
Title: {issue_title}
Description: {(issue_body or '')[:600]}
Labels: {issue_labels}

==================================================
CANDIDATE FILES
==================================================
{json.dumps(matched_files[:20], indent=2)}

Connected files in dependency graph:
{graph_context[:30]}

==================================================
TASKS
==================================================
1. Re-score each file 0.0-1.0 based on how likely it needs changes.
2. Estimate difficulty (easy/medium/hard).
   Core subsystems (routing, session, middleware, auth, async) = harder.
3. Estimate time to fix.
4. Explain your reasoning briefly.

Return ONLY valid JSON, no explanation, no markdown backticks:
{{
  "matched_files": [
    {{"file": "path/to/file.py", "score": 0.92, "reason": "why this file is relevant"}}
  ],
  "difficulty": "easy",
  "estimated_time": "1-2 hours",
  "reasoning": "brief explanation of the analysis"
}}"""
    return await reason(prompt, max_tokens=1200)


async def generate_contribution_steps(
    issue_title: str,
    issue_body: str,
    issue_labels: list[str],
    entry_files: list[str],
    dependency_chain: list[dict],
    experience: str,
    languages: list[str],
) -> dict:
    """Ask the LLM to generate a step-by-step contribution path."""
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

==================================================
ISSUE CONTEXT
==================================================
Issue Title: {issue_title}
Issue Summary: {(issue_body or '')[:500]}
Labels: {issue_labels}
Entry Point Files: {entry_files[:10]}
Dependency Chain (from graph traversal):
{json.dumps(dependency_chain[:20], indent=2)}

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
- Is this a PR? Reject.
- Are steps specific to THIS issue?
- Would this help someone fix it?
- Is architectural risk honestly communicated?

Return ONLY valid JSON, no explanation, no markdown backticks:
{{
  "contribution_path": [
    {{
      "step": 1,
      "file": "path/to/file.py",
      "action": "precise developer action",
      "reason": "engineering reasoning",
      "suggested_changes": "specific guidance on what to modify"
    }}
  ],
  "estimated_time": "realistic duration",
  "key_files": ["file1.py", "file2.py"],
  "tips": "one deep insight for this issue",
  "setup_commands": [],
  "testing_strategy": "intelligent validation approach"
}}"""
    return await reason(prompt, max_tokens=2000)


async def rank_issues_for_user(
    issues: list[dict],
    repo_files: list[str],
    user_profile: dict,
    max_results: int = 5,
) -> list[dict]:
    """Ask the LLM to rank pre-filtered issues for a specific user."""
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

Candidate issues (pre-filtered and pre-scored):
{json.dumps(issues[:20], indent=2)}

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
5. match_score (0-100) — scores must show real spread

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
    return await reason(prompt, max_tokens=1500)
