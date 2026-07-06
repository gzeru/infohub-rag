import streamlit as str_web
import os
import sys

# Interner Systempfad-Abgleich
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Direkter Import der verarbeitenden Pipeline und des Bild-Suchers
from infohub.pipeline import run_pipeline
from infohub.retrieval.search_engine import search_images

# 1. VISUELLE BEREINIGUNG
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

# 2. DIE REINE UI
str_web.title("🤖 InfoHub RAG Intelligence Engine")

user_query = str_web.text_input(
    "Stelle eine Frage an dein RAG-System:", 
    placeholder="Z.B. What is the difference between EEU and EEP in Ethiopia?"
)

# 3. INTERNE VERARBEITUNG & DIREKTE AUSGABE
if user_query.strip() != "":
    with str_web.spinner("Suche läuft..."):
        try:
            # Führt die Pipeline aus (liefert Antwort, Bilder und die bereinigte Query)
            pipeline_result = run_pipeline(user_query)
            
            # Die Antwort erscheint sofort direkt unter der Eingabe
            str_web.markdown("---")
            str_web.info(pipeline_result["answer"])
            
            # -----------------------------------------------------------------
            # NEU: Direkte Anzeige des im Kontext gefundenen Bildes (Methode 1)
            # -----------------------------------------------------------------
            if pipeline_result.get("has_image"):
                str_web.markdown("### 📌 Kontextuelle Abbildung")
                str_web.image(
                    pipeline_result["image_source"],
                    caption=pipeline_result["caption"],
                    width="stretch"
                )
            
            # -----------------------------------------------------------------
            # DER VISUELLE REFERENZ-LAYER (Zusätzliche Web-Bilder)
            # -----------------------------------------------------------------
            str_web.markdown("### 📸 Visuelle Referenzen / Images")
            
            # FALLBACK-STEUERUNG: Wir holen das übersetzte Englisch aus der Pipeline.
            # Falls nicht vorhanden, nutzen wir ein präzisiertes medizinisches Profil als Fallback.
            optimized_img_query = pipeline_result.get("english_query", "medical electric ring cutter tool")
            
            # Wenn der Nutzer nach einem Ring-Cutter sucht, erzwingen wir den medizinischen/Goldschmied-Kontext
            if "ring" in optimized_img_query.lower() and "cut" in optimized_img_query.lower():
                optimized_img_query = "medical motorized ring cutter rescue tool"
            
            # Nutzt jetzt die optimierte englische Query statt des rohen Amharisch!
            image_urls = search_images(optimized_img_query, max_results=3)
            
            if image_urls:
                cols = str_web.columns(len(image_urls))
                for idx, col in enumerate(cols):
                    with col:
                        str_web.image(
                            image_urls[idx], 
                            caption=f"Referenz {idx + 1}", 
                            width="stretch"
                        )
            else:
                str_web.write("Keine weiteren passenden Referenzbilder im Web gefunden.")
                
        except Exception as e:
            str_web.error(f"Fehler: {str(e)}")
