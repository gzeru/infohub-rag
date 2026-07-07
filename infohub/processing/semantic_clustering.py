import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Lazy-Loading oder globales Modell – bleibt schlank
model = SentenceTransformer("all-MiniLM-L6-v2")


def cluster_chunks(chunks: list, threshold: float = 0.70, max_clusters: int = 4) -> list:
    """
    Data-driven semantic clustering with defensive fallbacks:
    - Filters invalid/empty inputs.
    - Limits explosive cluster growth.
    - Groups isolated singletons into a single 'Miscellaneous' fallback cluster 
      to prevent XML bloating.
    """
    # 1. Defensiver Check gegen leere oder ungültige Listen
    if not chunks or not isinstance(chunks, list):
        return []

    # Bereinigung: Nur echte, nicht-leere Strings verarbeiten
    clean_chunks = [str(c).strip() for c in chunks if c and str(c).strip()]
    if not clean_chunks:
        return []

    try:
        embeddings = model.encode(clean_chunks)
    except Exception as e:
        print(f"[CLUSTERING-FEHLER] Embedding-Generierung fehlgeschlagen: {str(e)}")
        # Fallback: Gib alle bereinigten Chunks als ein einziges Notfall-Cluster zurück
        return [clean_chunks]

    cluster_indices = []

    for i, chunk in enumerate(clean_chunks):
        placed = False

        for cluster in cluster_indices:
            rep_idx = cluster[0]

            # Kosinus-Ähnlichkeit zwischen dem aktuellen Chunk und dem Repräsentanten
            sim = cosine_similarity(
                [embeddings[i]],
                [embeddings[rep_idx]]
            )[0][0]

            if sim >= threshold:
                cluster.append(i)
                placed = True
                break

        if not placed:
            cluster_indices.append([i])

    # 2. Post-Processing: Singletons (Einzelgänger) konsolidieren
    final_clusters_text = []
    miscellaneous_cluster = []

    for cluster in cluster_indices:
        actual_chunks = [clean_chunks[idx] for idx in cluster]
        
        # Wenn das Cluster nur aus einem einzigen Element besteht, sammeln wir es vorerst
        if len(actual_chunks) == 1:
            miscellaneous_cluster.extend(actual_chunks)
        else:
            final_clusters_text.append(actual_chunks)

    # Wenn wir Einzelgänger gefunden haben, fügen wir sie als ein gemeinsames Rest-Cluster hinzu
    if miscellaneous_cluster:
        final_clusters_text.append(miscellaneous_cluster)

    # 3. Sicherheitsdeckel: Begrenzung der Cluster-Anzahl für die Pipeline-Stabilität
    if len(final_clusters_text) > max_clusters:
        print(f"[CLUSTERING] Kritische Clustermenge erreicht ({len(final_clusters_text)}). Greife hart ein.")
        return final_clusters_text[:max_clusters]

    return final_clusters_text
