import streamlit as str_web
import os
import sys

# Interner Systempfad-Abgleich (passiert vollautomatisch im Hintergrund)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Direkter Import der verarbeitenden Pipeline und des neuen Bild-Suchers
from infohub.pipeline import run_pipeline
from infohub.retrieval.search_engine import search_images  # Importiert die neue Bild-Funktion

# 1. VISUELLE BEREINIGUNG: Sofortiger Start ohne Streamlit-Rahmenmenüs
str_web.set_page_config(page_title="InfoHub AI", page_icon="🤖", layout="centered")

hide_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 1rem;}
    </style>
"""
str_web.markdown(hide_style, unsafe_allow_html=True)

# 2. DIE REINE UI: Erscheint sofort als allererstes auf dem Bildschirm
str_web.title("🤖 InfoHub RAG Intelligence Engine")

user_query = str_web.text_input(
    "Stelle eine Frage an dein RAG-System:", 
    placeholder="Z.B. What is the difference between EEU and EEP in Ethiopia?"
)

# 3. INTERNE VERARBEITUNG & DIREKTE AUSGABE
if user_query.strip() != "":
    with str_web.spinner("Suche läuft..."):
        try:
            # Die Parameter (API-Keys, Schwellenwerte, Scopes) werden intern in der Pipeline versorgt
            # run_pipeline liefert nun ein Dictionary zurück
            pipeline_result = run_pipeline(user_query)
            
            # Die Antwort erscheint sofort direkt unter der Eingabe
            str_web.markdown("---")
            str_web.info(pipeline_result["answer"])
            
            # -----------------------------------------------------------------
            # NEU: Direkte Anzeige des im Kontext gefundenen Bildes (Methode 1)
            # -----------------------------------------------------------------
            if pipeline_result["has_image"]:
                str_web.markdown("### 📌 Kontextuelle Abbildung")
                str_web.image(
                    pipeline_result["image_source"],
                    caption=pipeline_result["caption"],
                    width="stretch"  # KORRIGIERT: Ersetzt use_container_width=True
                )
            
            # -----------------------------------------------------------------
            # DER VISUELLE REFERENZ-LAYER (Zusätzliche Web-Bilder)
            # -----------------------------------------------------------------
            str_web.markdown("### 📸 Visuelle Referenzen / Images")
            
            # Erntet bis zu 3 passende Bilder parallel zur Suchanfrage
            image_urls = search_images(user_query, max_results=3)
            
            if image_urls:
                # Erstellt nebeneinanderliegende Spalten für die Bildanzeige
                cols = str_web.columns(len(image_urls))
                for idx, col in enumerate(cols):
                    with col:
                        str_web.image(
                            image_urls[idx], 
                            caption=f"Referenz {idx + 1}", 
                            width="stretch"  # KORRIGIERT: Ersetzt use_container_width=True
                        )
            else:
                str_web.write("Keine weiteren passenden Referenzbilder im Web gefunden.")
                
        except Exception as e:
            str_web.error(f"Fehler: {str(e)}")
