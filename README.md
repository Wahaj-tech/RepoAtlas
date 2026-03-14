# RepoAtlas

RepoAtlas is an AI-powered open source contribution assistant.
It analyzes a GitHub repository, builds a dependency graph, matches issues to a developer profile, and generates practical contribution paths.

## What It Does

- Analyzes public GitHub repositories using GitHub APIs.
- Builds a code dependency graph from important source files.
- Recommends issues based on your:
  - preferred languages
  - experience level
  - available time
- Generates contribution steps for selected issues.
- Estimates file-change impact/risk from graph centrality and dependency paths.
- Provides graceful fallbacks when AI provider or rate limits fail.

## Key Features

- AI issue matching with deterministic fallback.
- AI contribution path generation with deterministic fallback.
- Language mismatch detection between repo and user profile.
- FastAPI backend with documented interactive API docs at /docs.
- React + Vite frontend with animated onboarding and dashboard.
- Dockerized full-stack deployment (frontend static build served by FastAPI).
- Railway deployment configuration included.

## Architecture

- Frontend: React + Vite (in frontend)
- Backend: FastAPI (in backend)
- Data source: GitHub REST API
- Graph engine: networkx
- AI provider: Groq (Llama 3.3 70B)
- Cache: in-memory Python dictionaries (process-local)

Flow:

1. User submits GitHub URL + profile in frontend.
2. Backend fetches repo metadata/tree/issues.
3. Backend selects important files and fetches contents.
4. Backend builds dependency graph.
5. Backend ranks issues via prefilter + AI reasoner (or fallback).
6. User selects issue; backend generates contribution path.
7. Frontend renders graph, matches, and step-by-step guidance.

## Project Structure

```text
repoAtlas/
  backend/
    main.py                  # FastAPI app, API routes, static serving
    requirements.txt
    models/
      schemas.py             # Request/response models
    routers/
      repo.py                # Main API endpoints
    services/
      analyzer_service.py    # GitHub fetch orchestration + file selection
      github_service.py      # GitHub API integration
      graph_service.py       # Graph building + impact analysis
      ai_service.py          # AI matching/path generation + fallbacks
      llm_reasoner.py        # Provider abstraction and structured prompts
      cache_service.py       # In-memory cache helpers
      matching_service.py    # Prefiltering logic
      issue_matcher.py       # Issue-level analysis
      contribution_path.py   # Alternative path generation logic

  frontend/
    src/
      pages/                 # Landing, Dashboard, IssuePage
      components/            # GraphView, ImpactPanel, IssueCard, etc.
      services/api.js        # Frontend API client

  Dockerfile                # Multi-stage frontend+backend image
  railway.toml              # Railway deploy config
```

## Prerequisites

- Python 3.11+ (3.13 also works locally in this repo)
- Node.js 20+ and npm
- Optional but recommended:
  - GitHub personal access token for higher API rate limits
  - Groq API key for AI-powered reasoning

## Environment Variables

Create backend/.env with:

```env
# Optional but recommended for GitHub API rate limits
GITHUB_TOKEN=your_github_token

# Required for AI reasoning (issue ranking/path generation)
GROQ_API_KEY=your_groq_api_key
```

Frontend optional env:

```env
# frontend/.env
# Defaults to /api if not set
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

Notes:

- If GROQ_API_KEY is missing, some AI operations fall back to deterministic heuristics.
- If GITHUB_TOKEN is missing, app still works but may hit GitHub rate limits faster.

## Local Development

### 1) Backend setup

From repo root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run backend:

```powershell
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Backend URLs:

- API root: http://127.0.0.1:8000/
- Health: http://127.0.0.1:8000/health
- Swagger docs: http://127.0.0.1:8000/docs

### 2) Frontend setup

From repo root:

```powershell
cd frontend
npm install
npm run dev
```

Frontend URL:

- http://127.0.0.1:5173 (or the port Vite prints)

### 3) Connect frontend to backend

By default frontend uses /api (proxy-style production path).
For local split-host development, set frontend/.env:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

Restart Vite after editing env files.

## Running With Existing VS Code Tasks

This workspace already includes tasks such as:

- Install Backend Deps
- Verify Backend Import
- RepoAtlas Backend Windows
- Start RepoAtlas / restart-server variants

You can run these from VS Code Command Palette:

- Tasks: Run Task

## Docker Run

Build image from repo root:

```bash
docker build -t repoatlas .
```

Run container:

```bash
docker run --rm -p 8000:8000 --env-file backend/.env repoatlas
```

The container serves:

- Backend API at /api
- Frontend static app at /

## Railway Deployment

This repo is configured for Dockerfile-based Railway deploy.

- railway.toml sets:
  - healthcheckPath = /health
  - restart policy on failure
- Dockerfile:
  - builds frontend in stage 1
  - installs backend deps in stage 2
  - copies frontend dist to backend static folder
  - runs uvicorn on PORT

Required Railway variables:

- GROQ_API_KEY
- GITHUB_TOKEN (recommended)

## API Endpoints

Base URL:

- Local: http://127.0.0.1:8000/api
- Production: /api

### GET /repo-languages

Query params:

- github_url (string)

Response:

```json
{
  "languages": ["Python", "TypeScript"],
  "primary": "Python"
}
```

### POST /analyze

Request:

```json
{
  "github_url": "https://github.com/owner/repo",
  "user_profile": {
    "languages": ["Python", "JavaScript"],
    "experience": "beginner",
    "time_available": "< 2 hours",
    "interests": ["backend"]
  }
}
```

Returns repository metadata, graph, recommendations, and language mismatch info.

### POST /match-issues

Request includes optional max_results and label_filter.
Returns ranked issue matches and scan summary.

### POST /contribution-path

Input:

- github_url
- issue_number
- user_profile

Returns contribution steps, key files, tips, and time estimate.

### POST /impact

Input:

- github_url
- file_path

Returns affected files, risk level, affected count, and centrality score.

### POST /analyze-issue

Analyzes a specific issue against repo graph context.

### POST /generate-path

Alternative path generation endpoint for a specific issue and profile.

## Frontend Scripts

From frontend:

```bash
npm run dev      # development server
npm run build    # production build
npm run preview  # preview build locally
```

## Backend Notes

- CORS is currently wide open (allow_origins = ["*"]).
- In-memory cache is process-local and resets on restart.
- Graph cache is also in-memory and rebuilt when needed.
- GitHub URL parsing supports full URLs and owner/repo shorthand in service layer.

## Troubleshooting

### groq package or API key errors

Symptoms:

- Runtime errors mentioning groq package not installed
- GROQ_API_KEY is not set

Fix:

```powershell
cd backend
pip install -r requirements.txt
```

Set backend/.env:

```env
GROQ_API_KEY=your_key
```

### GitHub rate limit issues

Symptoms:

- Empty issues/tree/metadata or degraded responses

Fix:

- Set GITHUB_TOKEN in backend/.env.
- Retry after rate limit reset.

### Frontend cannot reach backend

Symptoms:

- Network/404/CORS errors in browser console

Fix:

- Ensure backend is running on 127.0.0.1:8000.
- Set frontend/.env VITE_API_BASE_URL to http://127.0.0.1:8000/api.
- Restart frontend dev server.

## Security and Production Recommendations

- Restrict CORS allow_origins to trusted domains.
- Replace in-memory cache with Redis for multi-instance deployments.
- Add request rate limiting and structured logging.
- Add API authentication if exposing beyond trusted users.
- Store secrets only in environment variables, never in source control.

## Suggested Next Improvements

- Add automated tests for:
  - GitHub URL parsing
  - issue prefilter scoring
  - graph build and impact risk logic
- Add persistent caching and cache invalidation strategy.
- Add GitHub App integration for richer repo/issue context.
- Add CI pipeline for linting/tests/build.

## License

No explicit license file is currently present in this repository.
If you plan to open-source this project, add a LICENSE file (MIT/Apache-2.0/etc.) before publishing.
