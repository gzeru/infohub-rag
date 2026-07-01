from infohub.retrieval.search_engine import search
from infohub.retrieval.fetcher import fetch
from infohub.processing.text_extractor import extract_text
from infohub.processing.segmenter import segment_text
from infohub.processing.relevance import score_relevance
from infohub.processing.filter import is_meaningful
from infohub.processing.dedupe import is_duplicate
from infohub.core.query_scope import detect_scope
from infohub.processing.semantic_clustering import cluster_chunks
from infohub.processing.semantic_labeling import pick_representative_sentence

from urllib.parse import urlparse
from collections import defaultdict


def run_pipeline(query: str):
    # KORREKTUR 1: Expliziter Neustart des Ausgabezustands, um Speichergeister zu verhindern
    output = {}
    scored_chunks = []

    results = search(query)
    
    # Absicherung: Falls die Suchmaschine gar nichts liefert, sofort leer abbrechen
    if not results:
        print("Suchmaschine liefert keine Ergebnisse. Pipeline bricht sauber ab.")
        return {}

    # 1. Query scope
    scope = detect_scope(query)

    if scope == "broad":
        threshold = 0.35
    elif scope == "medium":
        threshold = 0.25
    else:
        threshold = 0.2

    # 2. Fetch + extract + chunk + score
    for result in results:
        url = result.get("url")
        ddg_snippet = result.get("snippet", "")  # Holen des Live-Textausschnitts von DDG
        
        if not url:
            continue

        print(f"Fetching: {url}")

        page = fetch(url)
        html = page.get("content", "")

        text = ""
        if html:
            text = extract_text(html)
        
        # KORREKTUR 2: Der generische Web-Fallback. 
        # Wenn Scraping fehlschlägt oder blockiert wird, retten wir die Pipeline mit dem DDG-Snippet.
        if not text and ddg_snippet:
            print(f"Scraping blockiert oder leer für {url}. Nutze DDG-Snippet als Fallback.")
            text = ddg_snippet

        if not text:
            continue

        chunks = segment_text(text)

        for chunk in chunks:
            if not is_meaningful(chunk):
                continue

            score = score_relevance(query, chunk)

            if score >= threshold:
                scored_chunks.append((score, chunk, url))

    # 3. Sort
    scored_chunks.sort(key=lambda x: x[0], reverse=True)

    # 4. Deduplicate + domain balance
    domain_count = defaultdict(int)
    filtered = []

    MAX_PER_DOMAIN = 3

    for score, chunk, url in scored_chunks:
        domain = urlparse(url).netloc

        if domain_count[domain] >= MAX_PER_DOMAIN:
            continue

        if is_duplicate(chunk, filtered):
            continue

        filtered.append(chunk)
        domain_count[domain] += 1

        if len(filtered) >= 10:
            break

    # 5. Semantic clustering
    clusters = cluster_chunks(filtered)

    # 6. Build output
    for i, cluster in enumerate(clusters):
        # Semantic representative sentence (IMPORTANT STEP)
        representative = pick_representative_sentence(query, cluster)

        # KORREKTUR 3: Robustes Labeling für das UI. 
        # Verhindert riesige Schachtelsätze oder unschöne Code-Fragmente in den Dictionary-Schlüsseln.
        if representative and len(representative) < 90 and "youtube" not in representative.lower():
            label = representative.strip()
        else:
            label = f"Relevante Suchergebnisse Gruppe {i+1}"

        output[label] = cluster[:3]

    return output
