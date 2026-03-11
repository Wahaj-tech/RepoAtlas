_cache = {}

def get_cache(key: str):
    return _cache.get(key)

def set_cache(key: str, value: dict):
    _cache[key] = value

def clear_cache():
    _cache.clear()