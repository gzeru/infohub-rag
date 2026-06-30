def detect_scope(query: str) -> str:
    q = query.strip().lower()
    words = q.split()

    if len(words) <= 1:
        return "broad"

    if len(words) <= 3:
        return "medium"

    return "specific"