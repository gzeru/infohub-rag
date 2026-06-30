from infohub.processing.relevance import score_relevance
import re


def pick_representative_sentence(query, cluster):
    """
    Selects the best matching chunk from a cluster and extracts a clean,
    short title phrase to use as a dictionary key instead of a raw sentence.
    """
    if not cluster:
        return "General Information"

    # 1. Find the chunk that matches the user's intent best
    best_chunk = max(
        cluster,
        key=lambda chunk: score_relevance(query, chunk)
    )

    # 2. Clean up common formatting debris (like brackets, citations, newlines)
    clean_chunk = re.sub(r'\[\s*\d+\s*\]', '', best_chunk)  # Removes [1], [ 2 ]
    clean_chunk = clean_chunk.replace('\n', ' ').strip()

    # 3. Try to split at a natural pause point (colon, dash, or period)
    delimiters = [":", " - ", " – ", "."]
    for delimiter in delimiters:
        if delimiter in clean_chunk:
            part = clean_chunk.split(delimiter)[0].strip()
            # Ensure the split part is a reasonable title length
            if 15 <= len(part) <= 50:
                return part

    # 4. Fallback: Take the first 5 words cleanly if no punctuation matches
    words = clean_chunk.split()
    if len(words) > 5:
        return " ".join(words[:5]) + "..."

    return clean_chunk[:40]