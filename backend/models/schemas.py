from pydantic import BaseModel
from typing import List, Optional

class UserProfile(BaseModel):
    languages: List[str]
    experience: str
    time_available: str

class AnalyzeRequest(BaseModel):
    github_url: str
    user_profile: UserProfile

class ImpactRequest(BaseModel):
    github_url: str
    file_path: str