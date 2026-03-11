from groq import Groq
import json
import os
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

async def get_recommendations(issues, graph, user_profile):
    issues_clean = [
        {
            "id": i.get("number"),
            "title": i.get("title"),
            "body": (i.get("body") or "")[:300],
            "labels": [l["name"] for l in i.get("labels", [])]
        }
        for i in issues[:20]
    ]

    prompt = f"""
    You are an expert open source contributor advisor.

    User Profile:
    - Languages known: {user_profile.get('languages')}
    - Experience level: {user_profile.get('experience')}
    - Time available: {user_profile.get('time_available')}

    Repository files (sample):
    {[n['id'] for n in graph['nodes'][:40]]}

    Open Issues:
    {json.dumps(issues_clean, indent=2)}

    Pick the TOP 3 issues most suitable for this user.
    Return ONLY valid JSON, no explanation, no markdown backticks:
    [
      {{
        "issue_id": 123,
        "title": "issue title",
        "why_good_match": "specific reason based on user profile",
        "difficulty": "easy",
        "files_to_look_at": ["file1.py", "file2.py"],
        "estimated_time": "1-2 hours",
        "match_score": 95
      }}
    ]
    """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
        temperature=0.3
    )

    raw = response.choices[0].message.content
    clean = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(clean)


async def get_contribution_path(issue, graph, experience):
    prompt = f"""
    You are an expert open source mentor.

    Issue: {issue.get('title')}
    Description: {(issue.get('body') or '')[:400]}
    Experience level: {experience}

    Repository files available:
    {[n['id'] for n in graph['nodes'][:40]]}

    Generate a specific step by step guide to fix this issue.
    Return ONLY valid JSON, no explanation, no markdown backticks:
    {{
      "steps": [
        {{
          "step": 1,
          "title": "short title",
          "action": "exactly what to do",
          "file": "specific_file.py",
          "why": "why this step matters"
        }}
      ],
      "estimated_total_time": "2-3 hours",
      "key_files": ["file1.py", "file2.py"],
      "tips": "one helpful tip for this specific issue"
    }}
    """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
        temperature=0.3
    )

    raw = response.choices[0].message.content
    clean = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(clean)