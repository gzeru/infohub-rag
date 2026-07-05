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
import os
from openai import OpenAI  # OpenAI-Bibliothek importiert


def build_xml_context_from_clusters(pipeline_output: dict) -> str:
    """
    Abstrakte Kapselungsebene: Transformiert semantische Text-Cluster in ein
    striktes XML-Schema, um syntaktische Barrieren für den Attention-Mechanismus
    des LLMs zu errichten. Verhindert die Verschmelzung von Attributen über Clustergrenzen hinweg.
    """
    if not pipeline_output:
        return "<search_knowledge_base>\n  <!-- Keine relevanten Daten gefunden -->\n</search_knowledge_base>"

    context_elements = ["<search_knowledge_base>"]
    
    node_id = 1
    for label, chunks in pipeline_output.items():
        for chunk in chunks:
            clean_chunk = chunk.strip() if isinstance(chunk, str) else str(chunk).strip()
            context_elements.append(f'  <source_node id="{node_id}">')
            context_elements.append(f"    <semantic_context>{label}</semantic_context>")
            context_elements.append(f"    <raw_fact_stream>\n{clean_chunk}\n    </raw_fact_stream>")
            context_elements.append(f"  </source_node>")
            node_id += 1
        
    context_elements.append("</search_knowledge_base>")
    return "\n".join(context_elements)


def get_zero_assumption_prompt() -> str:
    """
    Gibt die metakognitive Verarbeitungsvorschrift für das LLM in Englisch zurück.
    Funktioniert vollkommen sprachunabhängig für jede Sprache weltweit.
    """
    return (
        "[ROLE]\n"
        "You are the deterministic extraction module of the InfoHub RAG Intelligence Engine. "
        "Your sole task is to provide a strict, fact-based answer to the user's query.\n\n"
        "[PROCESSING DIRECTIVES]\n"
        "1. SOURCE ISOLATION: Analyze the data exclusively within the boundaries of each individual <source_node> tag. "
        "Treat them as isolated information units.\n"
        "2. ENTITY VALIDATION: If a text inside a <source_node> describes a historical change, split, "
        "merger, or predecessor organizations, strictly isolate their attributes. "
        "Only assign attributes to the requested entity that are explicitly valid for the current state (present tense) in the same sentence.\n"
        "3. COGNITIVE PROHIBITION: You are strictly forbidden from:\n"
        "    - Making logical assumptions not directly stated in the text.\n"
        "    - Merging facts from different <source_node> elements into a new claim unless explicitly linked in the text.\n"
        "    - Supplementing missing information with speculative general knowledge.\n"
        "4. GAP REPORTING: If the <search_knowledge_base> does not answer the question with absolute, unquestionable certainty, "
        "do not generate a plausible answer; instead, precisely name the incomplete points.\n\n"
        "[OUTPUT FORMAT]\n"
        "Answer directly, precisely, and purely factually. Do not use introductory phrases like 'Based on the documents...'.\n\n"
        "[STRICT ZERO-BIAS LANGUAGE COMPLIANCE]\n"
        "CRITICAL: You must automatically detect the exact language of the user's query.\n"
        "The final response MUST be written exclusively in that identical language. Never switch back to English, German, or any other language unless the query itself was written in it.\n"
        "CRITICAL: Do not output any meta-commentary, introductory explanations, or thoughts about this language mirror rule itself. Start directly with the translated fact extraction.\n\n"
        "[UNIVERSAL LINGUISTIC REFINEMENT]\n"
        "CRITICAL: When responding in the detected target language, you are strictly forbidden from "
        "simply transliterating English technical terms or entities phonetically into the target language's alphabet, script, or sounds.\n"
        "Instead, you MUST perform a full semantic translation. Translate the actual underlying meaning "
        "into the native, culturally authentic, and professionally accepted vocabulary of the target language.\n"
        "The terminology must read naturally to a native speaker and industry professional of that specific language."
    )


def run_pipeline(query: str) -> str:  # Rückgabetyp geändert zu str für die finale Antwort
    output = {}
    scored_chunks = []

    print(f"\n=== START PIPELINE-DEBUG FÜR QUERY: '{query}' ===")

    # API-Key Überprüfung für Groq vorab ausführen
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("[WARNUNG] Kein GROQ_API_KEY in Umgebungsvariablen gefunden! Breche vor LLM-Call ab.")
        return "Fehler: GROQ_API_KEY fehlt. Bitte in den Streamlit Secrets hinterlegen."

    # Initialisierung des universellen Clients (wird für Übersetzung und finale Generierung genutzt)
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1"
    )

    # =========================================================================
    # UNIVERSAL TRANSLATION LAYER (PRECISE ENGLISH PIVOT)
    # =========================================================================
    print("[DEBUG] Übersetze Suchanfrage universell ins Englische für maximalen Datenertrag...")
    try:
        translation_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "You are a strict cross-lingual semantic translation engine.\n"
                        "Your job is to translate the user's input into clear, grammatically correct English "
                        "while preserving the exact meaning of technical terms, institutional roles, and entities.\n"
                        "CRITICAL: Do not summarize, do not omit facts, and do not try to guess search keywords. "
                        "Provide a direct, high-fidelity translation so the semantic meaning remains 100% identical.\n"
                        "Output ONLY the raw English translation. No quotes, no explanations."
                    )
                },
                {"role": "user", "content": query}
            ],
            temperature=0.0  # Absolute Konstanz erzwingen
        )
        search_query = translation_response.choices[0].message.content.strip()
        print(f"[DEBUG] Original Query: '{query}' -> Engine Search Query: '{search_query}'")
    except Exception as e:
        print(f"[WARNUNG] Übersetzung fehlgeschlagen, nutze Original-Query als Fallback: {str(e)}")
        search_query = query

    # =========================================================================
    # EXTENSION: WEB RETRIEVAL MIT DER ENGLISCHEN QUERY
    # =========================================================================
    results = search(search_query)
    
    if not results:
        print("Suchmaschine liefert keine Ergebnisse. Pipeline bricht sauber ab.")
        return "Keine relevanten Suchergebnisse gefunden."
        
    if isinstance(results, str):
        print("[WARNUNG] 'results' wurde als String empfangen. Wandle in Notfall-Liste um.")
        results = [{"title": "Search Fallback", "url": "https://en.wikipedia.org", "snippet": results}]

    print(f"[DEBUG 1/6] Suchmaschine liefert {len(results)} Ergebnisse.")

    # 1. Query scope (wird anhand der englischen Suchphrase gemessen)
    scope = detect_scope(search_query)
    if scope == "broad":
        threshold = 0.35
    elif scope == "medium":
        threshold = 0.25
    else:
        threshold = 0.2
    print(f"[DEBUG 2/6] Erkanntes Scope: '{scope}' -> Threshold gesetzt auf: {threshold}")

    # 2. Fetch + extract + chunk + score
    for idx, result in enumerate(results):
        if isinstance(result, str):
            print(f" -> [{idx+1}/{len(results)}] Warnung: Einzelnes Resultat ist ein String. Nutze Fallback-Mapping.")
            url = "https://en.wikipedia.org"
            ddg_snippet = result
        elif isinstance(result, dict):
            url = result.get("url")
            ddg_snippet = result.get("snippet", "")
        else:
            print(f" -> [{idx+1}/{len(results)}] Unbekannter Element-Datentyp {type(result)}. Überspringe.")
            continue
        
        if not url:
            continue

        print(f" -> [{idx+1}/{len(results)}] Fetching: {url}")

        page = fetch(url)
        
        html = ""
        if isinstance(page, dict):
            html = page.get("content", "")
        elif isinstance(page, str):
            print(f"    [!] 'fetch' lieferte einen String statt eines Dictionarys. Verwende Text direkt.")
            html = page
        else:
            print(f"    [!] Unerwarteter Rückgabetyp von 'fetch': {type(page)}")

        text = ""
        if html:
            text = extract_text(html)
        
        if not text and ddg_snippet:
            print(f"    [!] Scraping blockiert/leer for {url}. Nutze DDG-Snippet als Fallback.")
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

            # WICHTIG: Wir matchen den englischen Text der Webseiten gegen das englische Such-Query
            score = score_relevance(search_query, chunk)

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
            representative = pick_representative_sentence(search_query, cluster)

            if representative and len(representative) < 90 and "youtube" not in representative.lower():
                label = representative.strip()
            else:
                label = f"Relevante Suchergebnisse Gruppe {i+1}"

            output[label] = cluster[:3]
    
    print(f"[DEBUG 6/6] Pipeline beendet. Output-Keys: {list(output.keys())}")
    
    # =========================================================================
    # WISSENS-EXTRAKTION VIA GROQ API
    # =========================================================================
    print("[DEBUG] Transformiere Cluster in XML-Schema...")
    xml_context = build_xml_context_from_clusters(output)
    system_prompt = get_zero_assumption_prompt()

    # --- PIPELINE DEBUG INPUT LOGS ---
    print("\n--- [PIPELINE DEBUG: LLM INPUTS] ---")
    print(f"System Prompt Length: {len(system_prompt)} chars")
    print(f"Language Compliance Target Section:\n{system_prompt[-350:]}")
    print(f"User Query Evaluated: '{query}'")
    print("------------------------------------\n")

    print("[DEBUG] Sende Daten und System-Prompt an die kostenlose Groq-API...")
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user", 
                    # Die originale Query des Nutzers bleibt hier bestehen,
                    # damit das Modell weiß, in welcher Sprache es antworten muss!
                    "content": f"DATA SET:\n{xml_context}\n\nUSER QUERY: {query}"
                }
            ],
            temperature=0.1
        )
        
        final_answer = response.choices[0].message.content
        
        # --- PIPELINE DEBUG OUTPUT LOGS ---
        print("\n--- [PIPELINE DEBUG: LLM OUTPUT] ---")
        print(f"LLM Raw Engine Response:\n{final_answer}")
        print("-------------------------------------\n")
        
        print("[DEBUG] Kostenlose LLM-Antwort via Groq erfolgreich generiert.")
        print("=== ENDE PIPELINE-DEBUG ===\n")
        return final_answer

    except Exception as e:
        print(f"[FEHLER] Fehler beim Groq-API-Aufruf: {str(e)}")
        print("=== ENDE PIPELINE-DEBUG ===\n")
        return f"Fehler bei der kostenlosen LLM-Generierung: {str(e)}"
