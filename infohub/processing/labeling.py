from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np


def extract_keywords(cluster, top_k=5):
    """
    Extract most important words from a cluster using TF-IDF.
    Fully data-driven: no predefined categories.
    """

    if not cluster:
        return []

    vectorizer = TfidfVectorizer(stop_words="english")
    X = vectorizer.fit_transform(cluster)

    scores = np.asarray(X.mean(axis=0)).flatten()
    words = vectorizer.get_feature_names_out()

    top_indices = scores.argsort()[::-1][:top_k]

    return [words[i] for i in top_indices]