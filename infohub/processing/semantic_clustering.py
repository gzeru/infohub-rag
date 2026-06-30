from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2")


def cluster_chunks(chunks, threshold=0.70):
    """
    Data-driven semantic clustering:
    - No keywords
    - No rules
    - Only meaning similarity
    """

    if not chunks:
        return []

    embeddings = model.encode(chunks)

    clusters = []

    for i, chunk in enumerate(chunks):

        placed = False

        for cluster in clusters:

            rep_idx = cluster[0]

            sim = cosine_similarity(
                [embeddings[i]],
                [embeddings[rep_idx]]
            )[0][0]

            if sim >= threshold:
                cluster.append(i)
                placed = True
                break

        if not placed:
            clusters.append([i])

    return [[chunks[i] for i in cluster] for cluster in clusters]