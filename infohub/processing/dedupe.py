def normalize(text: str) -> str:
    return " ".join(text.lower().split())


def is_duplicate(new_chunk: str, existing_chunks: list, threshold: float = 0.85) -> bool:
    """
    Simple heuristic dedup:
    - exact match OR strong overlap
    """
    new_norm = normalize(new_chunk)

    for chunk in existing_chunks:
        if normalize(chunk) == new_norm:
            return True

        # lightweight overlap check
        overlap = len(set(new_norm.split()) & set(normalize(chunk).split()))
        union = len(set(new_norm.split()) | set(normalize(chunk).split()))

        if union > 0 and (overlap / union) > threshold:
            return True

    return False