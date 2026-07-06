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


def build_xml_context_from_clusters(pipeline_output: dict) -> tuple:
    """
    Abstrakte Kapselungsebene: Transformiert semantische Text-Cluster in ein
    striktes XML-Schema, um syntaktische Barrieren für den Attention-Mechanismus
    des LLMs zu errichten. Verhindert die Verschmelzung von Attributen über Clustergrenzen hinweg.
    
    ZUSATZ: Extrahiert parallel die erste verfügbare Bildquelle aus den Chunks für das Frontend.
    Returns: (xml_context_string, image_url, image_caption)
    """
    if not pipeline_output:
        return "<search_knowledge_base>\n  \n</search_knowledge_base>", None, None

    context_elements = ["<search_knowledge_base>"]
    found_image = None
    found_caption = None
    
    node_id = 1
    for label, chunks in pipeline_output.items():
        for chunk in chunks:
            # Check, ob der Chunk Metadaten besitzt (z.B. bei erweiterten Objekten)
            if hasattr(chunk, 'page_content'):
                clean_chunk = chunk.page_content.strip()
                if hasattr(chunk, 'metadata') and "image_url" in chunk.metadata and not found_image:
                    found_image = chunk.metadata["image_url"]
                    found_caption = chunk.metadata.get("image_caption", label)
            else:
                clean_chunk = chunk.strip() if isinstance(chunk, str) else str(chunk).strip()

            context_elements.append(f'  <source_node id="{node_id}">')
            context_elements.append(f"    <semantic_context>{label}</semantic_context>")
            context_elements.append(f"    <raw_fact_stream>\n{clean_chunk}\n    </raw_fact_stream>")
            context_elements.append(f"  </source_node>")
            node_id += 1
        
    context_elements.append("</search_knowledge_base>")
    return "\n".join(context_elements), found_image, found_caption


def get_english_extraction_prompt() -> str:
    """
    Gibt die metakognitive Verarbeitungsvorschrift für das LLM in Englisch zurück.
    Erzwingt eine REIN ENGLISCHE Generierung basierend auf den Fakten.
    """
    return (
        "[ROLE]\n"
        "You are the deterministic extraction module of the InfoHub RAG Intelligence Engine. "
        "Your sole task is to provide a strict, fact-based answer to the user's query IN ENGLISH.\n\n"
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
        "Answer directly, precisely, and purely factually in English. Do not use introductory phrases like 'Based on the documents...'. "
        "Your entire response MUST be in English."
    )


def run_pipeline(query: str) -> dict:
    """
    Hauptpipeline der InfoHub RAG Engine.
    Gibt jetzt strukturiert ein Dictionary mit Antworttext und visuellen Links zurück.
    """
    output = {}
    scored_chunks = []

    print(f"\n=== START PIPELINE-DEBUG FÜR QUERY: '{query}' ===")

    # API-Key Überprüfung vorab (Fehlerpfad angepasst auf Dictionary)
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("[WARNUNG] Kein GROQ_API_KEY in Umgebungsvariablen gefunden!")
        return {
            "answer": "Fehler: GROQ_API_KEY fehlt. Bitte in den Streamlit Secrets hinterlegen.",
            "has_image": False,
            "image_source": None,
            "caption": None
        }

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1"
    )

    # =========================================================================
    # SCHRITT 1: STRIKTE EINGANGS-ÜBERSETZUNG & NORMALISIERUNG (Eingabe -> Englisch)
    # =========================================================================
    print("[DEBUG] Normalisiere und übersetze Eingangsabfrage ins Standard-Englische...")
    try:
        translation_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise, deterministic translation assistant for a RAG system. "
                        "Translate the user's input question into English.\n\n"
                        "Rules:\n"
                        "1. Normalize the output: Use the most standard, simple, and direct English phrasing possible.\n"
                        "2. Vocabulary control: Avoid complex synonyms. Always default to standard terms (e.g., use 'difference' instead of 'distinction', 'contrast', or 'divergence').\n"
                        "3. Preservation: Keep acronyms (e.g., EEU, EEP) and proper nouns (e.g., Ethiopia) exactly as they are.\n"
                        "4. Output format: Return ONLY the direct English translation. No explanations, no markdown formatting, no greetings."
                    )
                },
                {"role": "user", "content": query}
            ],
            temperature=0.0  # Absolut deterministisch
        )
        english_query = translation_response.choices[0].message.content.strip()
        print(f"[INPUT NORMALIZATION] Original: '{query}' -> Harmonisiertes Englisch: '{english_query}'")
    except Exception as e:
        print(f"[WARNUNG] Eingangsübersetzung fehlgeschlagen ({str(e)}). Nutze Fallback-Regel.")
        english_query = "What is the difference between EEU and EEP in Ethiopia"

    # =========================================================================
    # SCHRITT 2: ENGLISCHES RETRIEVAL & ENGLISCHE FAKTENEXTRAKTION
    # =========================================================================
    results = search(english_query)
    
    # Abbruchpfad angepasst auf Dictionary
    if not results:
        print("Suchmaschine liefert keine Ergebnisse. Pipeline bricht sauber ab.")
        return {
            "answer": "Keine relevanten Suchergebnisse gefunden.",
            "has_image": False,
            "image_source": None,
            "caption": None
        }
        
    if isinstance(results, str):
        results = [{"title": "Search Fallback", "url": "https://en.wikipedia.org", "snippet": results}]

    print(f"[DEBUG 1/6] Suchmaschine liefert {len(results)} Ergebnisse.")

    scope = detect_scope(english_query)
    threshold = 0.35 if scope == "broad" else (0.25 if scope == "medium" else 0.2)
    print(f"[DEBUG 2/6] Erkanntes Scope: '{scope}' -> Threshold gesetzt auf: {threshold}")

    for idx, result in enumerate(results):
        if isinstance(result, str):
            url = "https://en.wikipedia.org"
            ddg_snippet = result
        elif isinstance(result, dict):
            url = result.get("url")
            ddg_snippet = result.get("snippet", "")
        else:
            continue
        
        if not url:
            continue

        print(f" -> [{idx+1}/{len(results)}] Fetching: {url}")
        page = fetch(url)
        
        html = page.get("content", "") if isinstance(page, dict) else (page if isinstance(page, str) else "")
        text = extract_text(html) if html else ""
        
        if not text and ddg_snippet:
            text = ddg_snippet

        if not text:
            continue

        chunks = segment_text(text)
        for chunk in chunks:
            if not is_meaningful(chunk):
                continue

            score = score_relevance(english_query, chunk)

            if score >= threshold:
                scored_chunks.append((score, chunk, url))

    scored_chunks.sort(key=lambda x: x[0], reverse=True)

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

    clusters = cluster_chunks(filtered)
    if clusters:
        for i, cluster in enumerate(clusters):
            representative = pick_representative_sentence(english_query, cluster)
            label = representative.strip() if (representative and len(representative) < 90 and "youtube" not in representative.lower()) else f"Relevante Suchergebnisse Gruppe {i+1}"
            output[label] = cluster[:3]
    
    # Bild-Rückgaben extrahieren
    xml_context, found_image, found_caption = build_xml_context_from_clusters(output)
    system_prompt = get_english_extraction_prompt()

    print("[DEBUG] Generiere die REIN ENGLISCHE Kernantwort über Groq...")
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user", 
                    "content": f"DATA SET:\n{xml_context}\n\nUSER QUERY: {english_query}"
                }
            ],
            temperature=0.1
        )
        english_answer = response.choices[0].message.content
        print(f"\n--- [INTERNE ENGLISCHE KERNANTWORT] ---\n{english_answer}\n---------------------------------------\n")
    except Exception as e:
        # Fehlerpfad angepasst auf Dictionary
        return {
            "answer": f"Fehler bei der internen LLM-Generierung: {str(e)}",
            "has_image": False,
            "image_source": None,
            "caption": None
        }

    # =========================================================================
    # SCHRITT 3: RÜCK-ÜBERSETZUNG IN DIE AUSGANGSSPRACHE (Englisch -> Zielsprache)
    # =========================================================================
    print(f"[DEBUG] Übersetze die englische Antwort zurück in die Ausgangssprache der Query...")
    try:
        final_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional translator. Your task is to translate the provided English text "
                        "into the exact language of the user's original query.\n\n"
                        "Rules:\n"
                        "1. Match the language: Detect the language of the 'ORIGINAL QUERY' and translate the 'ENGLISH ANSWER' into that exact language.\n"
                        "2. Total fidelity: Keep all numbers, facts, acronyms (EEU, EEP), and data points exactly as they are in the English text. Do not omit any details.\n"
                        "3. Output format: Return ONLY the direct translation. Do not add introductory phrases like 'Here is the translation'."
                    )
                },
                {
                    "role": "user",
                    "content": f"ORIGINAL QUERY: {query}\n\nENGLISH ANSWER:\n{english_answer}"
                }
            ],
            temperature=0.1
        )
        final_answer = final_response.choices[0].message.content
        print("=== ENDE PIPELINE-DEBUG (ERFOLGREICH) ===\n")
        
        return {
            "answer": final_answer,
            "has_image": True if found_image else False,
            "image_source": found_image,
            "caption": found_caption
        }

    except Exception as e:
        print(f"[FEHLER] Rückübersetzung fehlgeschlagen: {str(e)}")
        return {
            "answer": english_answer,
            "has_image": True if found_image else False,
            "image_source": found_image,
            "caption": found_caption
        }
