from collections import defaultdict
import math


def simple_similarity(a: str, b: str) -> float:
    set_a = set(a.lower().split())
    set_b = set(b.lower().split())

    if not set_a or not set_b:
        return 0.0

    return len(set_a & set_b) / len(set_a | set_b)


def cluster_chunks(chunks, threshold: float = 0.25):

    clusters = []

    for chunk in chunks:

        placed = False

        for cluster in clusters:

            # compare with cluster representative
            rep = cluster[0]

            if simple_similarity(chunk, rep) >= threshold:
                cluster.append(chunk)
                placed = True
                break

        if not placed:
            clusters.append([chunk])

    return clusters