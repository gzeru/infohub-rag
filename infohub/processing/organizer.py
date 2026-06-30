from collections import defaultdict

def _to_words(text):
    return set(
        w.lower().strip(".,()[]{}:;\"'")
        for w in text.split()
        if len(w) > 3
    )

def _similarity(a_words, b_words):
    if not a_words or not b_words:
        return 0.0

    intersection = a_words.intersection(b_words)
    union = a_words.union(b_words)

    return len(intersection) / len(union)

def group_similar_chunks(chunks, threshold=0.18):
    clusters = []
    used = set()

    # precompute word sets
    word_sets = [_to_words(c) for c in chunks]

    for i in range(len(chunks)):
        if i in used:
            continue

        base = chunks[i]
        base_words = word_sets[i]

        cluster = [base]
        used.add(i)

        for j in range(i + 1, len(chunks)):
            if j in used:
                continue

            sim = _similarity(base_words, word_sets[j])

            if sim >= threshold:
                cluster.append(chunks[j])
                used.add(j)

        clusters.append(cluster)

    # label clusters automatically (no hardcoding)
    return {
        f"Group {i+1}": cluster
        for i, cluster in enumerate(clusters)
    }


def organize_fragments(chunks):
    return group_similar_chunks(chunks)