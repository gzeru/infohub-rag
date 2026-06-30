import re


def score_relevance(query: str, chunk: str) -> float:
    """
    Calculates a normalized overlap score between the query and text chunk,
    ignoring punctuation and common filler words to focus on true semantic intent.
    """
    # 1. Clean punctuation and lower-case both inputs
    clean_query = re.sub(r'[^\w\s]', '', query.lower())
    clean_chunk = re.sub(r'[^\w\s]', '', chunk.lower())

    # 2. Extract unique terms
    query_terms = set(clean_query.split())
    chunk_terms = set(clean_chunk.split())

    if not query_terms:
        return 0.0

    # 3. Define basic stop words to ignore (prevents false matches on grammar filler)
    stop_words = {"in", "the", "of", "and", "a", "an", "to", "is", "for", "on", "at", "by"}

    # Filter query terms down to meaningful keywords if possible
    meaningful_query_terms = query_terms - stop_words

    # Fallback to full query terms if the query consists entirely of stop words
    if not meaningful_query_terms:
        meaningful_query_terms = query_terms

    # 4. Calculate intersection based on core keyword intent
    overlap = meaningful_query_terms.intersection(chunk_terms)

    # Return ratio of matched key intent words
    return len(overlap) / len(meaningful_query_terms)