def safe_list(value):
    return value if isinstance(value, list) else []

def safe_dict(value):
    return value if isinstance(value, dict) else {}
