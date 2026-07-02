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

    print(f"\n=== START PIPELINE-DEBUG FÜR QUERY: '{query}' ===")

    results = search(query)
    print(f"[DEBUG 1/6] Suchmaschine liefert {len(results) if results else 0} Ergebnisse.")
    
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
    print(f"[DEBUG 2/6] Erkanntes Scope: '{scope}' -> Threshold gesetzt auf: {threshold}")

    # 2. Fetch + extract + chunk + score
    for idx, result in enumerate(results):
        url = result.get("url")
        ddg_snippet = result.get("snippet", "")  # Holen des Live-Textausschnitts von DDG
        
        if not url:
            continue

        print(f" -> [{idx+1}/{len(results)}] Fetching: {url}")

        page = fetch(url)
        html = page.get("content", "")

        text = ""
        if html:
            text = extract_text(html)
        
        # KORREKTUR 2: Der generische Web-Fallback. 
        if not text and ddg_snippet:
            print(f"    [!] Scraping blockiert/leer für {url}. Nutze DDG-Snippet als Fallback.")
            text = ddg_snippet

        if not text:
            print(f"    [!] Kein Text extrahierbar für {url}")
            continue

        chunks = segment_text(text)
        print(f"    [i] Text in {len(chunks)} Chunks zerlegt.")

        valid_chunks_count = 0
        passed_threshold_count = 0

        for chunk in chunks:
            if not is_meaningful(chunk):
                continue
            valid_chunks_count += 1

            score = score_relevance(query, chunk)

            if score >= threshold:
                scored_chunks.append((score, chunk, url))
                passed_threshold_count += 1
        
        print(f"    [i] Relevanz-Check: {valid_chunks_count} sinnvolle Chunks geprüft. {passed_threshold_count} überstanden den Threshold.")

    print(f"[DEBUG 3/6] Insgesamt gesammelt vor Duplikatfilter: {len(scored_chunks)} Chunks.")

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

    print(f"[DEBUG 4/6] Nach Deduplizierung & Domain-Check übrig: {len(filtered)} Chunks.")

    # 5. Semantic clustering
    clusters = cluster_chunks(filtered)
    print(f"[DEBUG 5/6] Semantisches Clustering liefert {len(clusters) if clusters else 0} Gruppen.")

    # 6. Build output
    if clusters:
        for i, cluster in enumerate(clusters):
            # Semantic representative sentence (IMPORTANT STEP)
            representative = pick_representative_sentence(query, cluster)

            # KORREKTUR 3: Robustes Labeling für das UI. 
            if representative and len(representative) < 90 and "youtube" not in representative.lower():
                label = representative.strip()
            else:
                label = f"Relevante Suchergebnisse Gruppe {i+1}"

            output[label] = cluster[:3]
    
    print(f"[DEBUG 6/6] Pipeline beendet. Output-Keys: {list(output.keys())}")
    print("=== ENDE PIPELINE-DEBUG ===\n")

    return output
