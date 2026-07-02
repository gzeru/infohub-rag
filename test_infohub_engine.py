import os
import sys

# Stellt sicher, dass Python das infohub-Verzeichnis im Pfad findet
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from infohub.retrieval.search_engine import search
from infohub.pipeline import run_pipeline, build_xml_context_from_clusters, get_zero_assumption_prompt

print("=" * 60)
print("       INFOHUB RAG INTELLIGENCE ENGINE - COMPONENT TEST")
print("=" * 60)

# Unsere Testfrage zu den äthiopischen Energiebehörden
test_query = "What is the difference between EEU and EEP?"

# ----------------------------------------------------------------
# SCHRITT 1: Isolierter Test der Suchmaschine (Tavily-Check)
# ----------------------------------------------------------------
print("\n[STEP 1/3] Teste search_engine.py (Datenquelle)...")
raw_results = search(test_query, max_results=2)

print(f" -> Datentyp der Rückgabe: {type(raw_results)}")
if isinstance(raw_results, list):
    print(f" -> Erfolg! {len(raw_results)} rohe Ergebnisse extrahiert.")
    if len(raw_results) > 0:
        print(f" -> Struktur-Check (Erstes Element): {type(raw_results[0])}")
        print(f"    - Title: {raw_results[0].get('title')}")
        print(f"    - URL: {raw_results[0].get('url')}")
else:
    print(f" -> [FEHLER] Die Suchmaschine liefert keine Liste, sondern: {type(raw_results)}")
    sys.exit(1)

# ----------------------------------------------------------------
# SCHRITT 2: Test der Pipeline (Fetching, Clustering, Labeling)
# ----------------------------------------------------------------
print("\n[STEP 2/3] Teste infohub/pipeline.py (Verarbeitung)...")
pipeline_output = run_pipeline(test_query)

print(f" -> Pipeline-Rückgabe erhalten (Datentyp: {type(pipeline_output)})")
print(f" -> Generierte semantische Gruppen: {list(pipeline_output.keys())}")

# ----------------------------------------------------------------
# SCHRITT 3: Test der XML-Kapselung & Prompts (LLM-Vorbereitung)
# ----------------------------------------------------------------
print("\n[STEP 3/3] Teste XML-Strukturierung & System-Prompt...")
xml_context = build_xml_context_from_clusters(pipeline_output)
system_prompt = get_zero_assumption_prompt()

print("\n--- GENERIERTES XML-SCHEMA FÜR DAS LLM (VORSCHAU) ---")
# Zeige die ersten 15 Zeilen des XML-Kontexts zur visuellen Überprüfung
print("\n".join(xml_context.split("\n")[:15]) + "\n  ...")

print("\n--- PROZESSVORSCHRIFT (SYSTEM PROMPT) ---")
print(system_prompt[:250] + " ... [gekürzt] ...")

print("\n" + "=" * 60)
print(" TEST BEENDET: Wenn bis hierher kein Absturz kam, ist alles perfekt!")
print("=" * 60)
