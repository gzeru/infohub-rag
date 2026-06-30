import streamlit as str_web
import os
import sys

# Wir fügen das aktuelle Verzeichnis zum Pfad hinzu, damit Python deine Engine findet
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importiere deine originale RAG-Pipeline
from infohub.pipeline import run_pipeline
from infohub.generation.generator import generate_answer

# Styling der Webseite
str_web.set_page_config(page_title="InfoHub RAG Engine", page_icon="🤖", layout="centered")
str_web.title("🤖 InfoHub RAG Intelligence Engine")
str_web.markdown("---")

# Das Eingabefeld
user_query = str_web.text_input("Stelle eine Frage an dein RAG-System:", placeholder="Z.B. Healthcare in the USA...")

if str_web.button("Frag KI", type="primary"):
    if user_query.strip() == "":
        str_web.warning("Bitte gib zuerst eine Frage ein!")
    else:
        # Schicker Lade-Kreisel, während die Pipeline arbeitet
        with str_web.spinner("Suche im Web und generiere Antwort... Bitte warten..."):
            try:
                # 1. Deine originale Pipeline ausführen
                structured_results = run_pipeline(user_query)
                # --- DIESE DEBUG-ZEILEN HINZUFÜGEN ---
                str_web.subheader("🔍 Debug-Ansicht der Pipeline:")
                str_web.write("Rohdaten aus der Pipeline (Typ):", type(structured_results))
                str_web.write("Inhalt der Ergebnisse:", structured_results)
                str_web.markdown("---")
                # -------------------------------------
                # 2. Antwort generieren
                final_answer = generate_answer(user_query, structured_results)

                # 3. Ergebnis anzeigen
                str_web.success("Antwort erfolgreich generiert!")
                str_web.markdown(f"**Aktuelle Suchanfrage:** *{user_query}*")
                str_web.info(final_answer)

            except Exception as e:
                str_web.error(f"Fehler bei der Verarbeitung: {str(e)}")