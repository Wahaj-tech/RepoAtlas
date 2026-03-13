_cache = {}


def get_cache_key(github_url: str, user_profile: dict = None):
    base = github_url.strip().lower()
    if user_profile:
        languages = sorted(user_profile.get("languages", []))
        experience = user_profile.get("experience", "")
        lang_str = "_".join(languages)
        return f"{base}_{lang_str}_{experience}"
    return base

def get_cache(key: str):
    return _cache.get(key)

def set_cache(key: str, value: dict):
    _cache[key] = value

def clear_cache():
    _cache.clear()