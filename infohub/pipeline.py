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
    Gibt die metakognitive Verarbeitungsvorschrift für das LLM zurück.
    Löst das Problem von Fehlallokationen bei Entitätenwechseln abstrakt und generisch.
    """
    return (
        "[ROLLE]\n"
        "Du bist das deterministische Extraktions-Modul der InfoHub RAG Intelligence Engine. "
        "Deine Aufgabe ist die strikte, faktenbasierte Beantwortung der Nutzeranfrage.\n\n"
        "[PROZESSVORSCHRIFT]\n"
        "1. QUELLEN-ISOLATION: Analysiere die Daten ausschließlich innerhalb der Grenzen jedes einzelnen <source_node>-Tags. "
        "Behandle sie als isolierte Informationseinheiten.\n"
        "2. ENTITÄTEN-VALIDIERUNG: Wenn ein Text innerhalb eines <source_node> einen historischen Wandel, "
        "eine Aufspaltung, eine Fusion oder Vorgängerorganisationen beschreibt, isoliere deren Attribute strikt. "
        "Ordne der angefragten Entität NUR Attribute zu, die im selben Satz explizit für den aktuellen Zustand (Gegenwart) gültig sind.\n"
        "3. KOGNITIVES VERBOT: Es ist dir strengstens untersagt:\n"
        "    - Logische Annahmen zu treffen, die nicht direkt im Text stehen.\n"
        "    - Fakten aus unterschiedlichen <source_node>-Elementen zu einer neuen Behauptung zu verschmelzen, wenn diese nicht explizit im Text verknüpft sind.\n"
        "    - Fehlende Informationen durch spekulatives Allgemeinwissen zu komplementieren.\n"
        "4. LÜCKEN-MELDUNG: Wenn die <search_knowledge_base> die Frage nicht mit absoluter, zweifelsfreier Sicherheit beantwortet, "
        "generiere keine plausible Antwort, sondern benenne präzise die unvollständigen Punkte.\n\n"
        "[AUSGABEFORMAT]\n"
        "Antworte direkt, präzise und rein sachlich. Verwende keine einleitenden Floskeln wie 'Basierend auf den Dokumenten...'.\n\n"
        "[LANGUAGE COMPLIANCE]\n"
        "CRITICAL RULE: Always respond in the exact same language that the user used for their query! "
        "If the query is in English, reply in English. If the query is in German, reply in German. If it is in Amharic, reply in Amharic."
    )


def run_pipeline(query: str) -> str:  # Rückgabetyp geändert zu str für die finale Antwort
    output = {}
    scored_chunks = []

    print(f"\n=== START PIPELINE-DEBUG FÜR QUERY: '{query}' ===")

    results = search(query)
    
    if not results:
        print("Suchmaschine liefert keine Ergebnisse. Pipeline bricht sauber ab.")
        return "Keine relevanten Suchergebnisse gefunden."
        
    if isinstance(results, str):
        print("[WARNUNG] 'results' wurde als String empfangen. Wandle in Notfall-Liste um.")
        results = [{"title": "Search Fallback", "url": "https://en.wikipedia.org", "snippet": results}]

    print(f"[DEBUG 1/6] Suchmaschine liefert {len(results)} Ergebnisse.")

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
        # SICHERHEITS-CHECK: Falls ein einzelnes Ergebnis ein String ist
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
        
        # --- SICHERHEITS-CHECK GEGEN DEN 'str' OBJECT HAS NO ATTRIBUTE 'get' FEHLER ---
        html = ""
        if isinstance(page, dict):
            html = page.get("content", "")
        elif isinstance(page, str):
            print(f"    [!] 'fetch' lieferte einen String statt eines Dictionarys. Verwende Text direkt als HTML/Snippet.")
            html = page
        else:
            print(f"    [!] Unerwarteter Rückgabetyp von 'fetch': {type(page)}")
        # -------------------------------------------------------------------------------

        text = ""
        if html:
            text = extract_text(html)
        
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
            representative = pick_representative_sentence(query, cluster)

            if representative and len(representative) < 90 and "youtube" not in representative.lower():
                label = representative.strip()
            else:
                label = f"Relevante Suchergebnisse Gruppe {i+1}"

            output[label] = cluster[:3]
    
    print(f"[DEBUG 6/6] Pipeline beendet. Output-Keys: {list(output.keys())}")
    
    # =========================================================================
    # ZU 100% KOSTENLOS: ANBINDUNG AN DIE GROQ API (OPENAI-KOMPATIBEL)
    # =========================================================================
    print("[DEBUG] Transformiere Cluster in XML-Schema...")
    xml_context = build_xml_context_from_clusters(output)
    system_prompt = get_zero_assumption_prompt()

    # API-Key Überprüfung für Groq
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("[WARNUNG] Kein GROQ_API_KEY in Umgebungsvariablen gefunden! Breche vor LLM-Call ab.")
        return "Fehler: GROQ_API_KEY fehlt. Bitte in den Streamlit Secrets hinterlegen."

    print("[DEBUG] Sende Daten und System-Prompt an die kostenlose Groq-API...")
    try:
        # Wir nutzen den universellen OpenAI-Client, leiten ihn aber zu Groq um
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # Dauerhaft kostenloses, extrem starkes Open-Source Modell
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Hier ist die Datenbasis:\n{xml_context}\n\nAntworte auf die Query: {query}"}
            ],
            temperature=0.1  # Niedrige Temperatur für faktengetreue RAG-Antworten
        )
        
        final_answer = response.choices[0].message.content
        print("[DEBUG] Kostenlose LLM-Antwort via Groq erfolgreich generiert.")
        print("=== ENDE PIPELINE-DEBUG ===\n")
        return final_answer

    except Exception as e:
        print(f"[FEHLER] Fehler beim Groq-API-Aufruf: {str(e)}")
        print("=== ENDE PIPELINE-DEBUG ===\n")
        return f"Fehler bei der kostenlosen LLM-Generierung: {str(e)}"
