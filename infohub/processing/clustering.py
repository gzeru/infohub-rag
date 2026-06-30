from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)


def cluster_chunks(chunks, threshold=0.70):

    embeddings = model.encode(chunks)

    clusters = []

    for idx, chunk in enumerate(chunks):

        assigned = False

        for cluster in clusters:

            representative = cluster[0]

            sim = cosine_similarity(
                [embeddings[idx]],
                [embeddings[representative]]
            )[0][0]

            if sim >= threshold:

                cluster.append(idx)
                assigned = True
                break

        if not assigned:
            clusters.append([idx])

    return [
        [chunks[i] for i in cluster]
        for cluster in clusters
    ]