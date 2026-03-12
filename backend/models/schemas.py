from pydantic import BaseModel
from typing import List, Optional

class UserProfile(BaseModel):
    languages: List[str]
    experience: str  # "beginner", "intermediate", "advanced"
    time_available: str
    interests: Optional[List[str]] = None  # e.g. ["testing", "docs", "bugfix"]

class AnalyzeRequest(BaseModel):
    github_url: str
    user_profile: UserProfile

class ImpactRequest(BaseModel):
    github_url: str
    file_path: str

class MatchIssuesRequest(BaseModel):
    github_url: str
    user_profile: UserProfile
    max_results: Optional[int] = 5
    label_filter: Optional[List[str]] = None

class ContributionPathRequest(BaseModel):
    github_url: str
    issue_number: int
    user_profile: UserProfile

# --- New AI Layer Schemas ---

class AnalyzeIssueRequest(BaseModel):
    """Input for POST /analyze-issue"""
    github_url: str
    issue_number: int

class GeneratePathRequest(BaseModel):
    """Input for POST /generate-path"""
    github_url: str
    issue_number: int
    user_profile: UserProfile

# --- Response schemas ---

class MatchedFile(BaseModel):
    file: str
    score: float
    reason: Optional[str] = None
    match_type: Optional[str] = None
    centrality: Optional[float] = None

class AnalyzeIssueResponse(BaseModel):
    issue: str
    keywords_extracted: Optional[List[str]] = None
    matched_files: List[MatchedFile]
    difficulty: str
    estimated_time: str
    reasoning: Optional[str] = None

class PathStep(BaseModel):
    step: int
    file: str
    action: str
    reason: str
    suggested_changes: Optional[str] = None

class GeneratePathResponse(BaseModel):
    issue: dict
    analysis: dict
    contribution_path: List[PathStep]
    estimated_time: str
    key_files: List[str]
    tips: str
    setup_commands: Optional[List[str]] = None
    testing_strategy: Optional[str] = None

class MatchedIssue(BaseModel):
    issue_id: int
    title: str
    why_good_match: str
    difficulty: str
    files_to_look_at: List[str]
    estimated_time: str
    match_score: int
    labels: Optional[List[str]] = None
    url: Optional[str] = None

class ContributionStep(BaseModel):
    step: int
    title: str
    action: str
    file: Optional[str] = None
    why: str

class ContributionPath(BaseModel):
    issue_id: int
    issue_title: str
    steps: List[ContributionStep]
    estimated_total_time: str
    key_files: List[str]
    tips: str
    setup_commands: Optional[List[str]] = None