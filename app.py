import streamlit as str_web
import os
import sys
from urllib.parse import urlparse

# Interner Systempfad-Abgleich
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Direkter Import der verarbeitenden Pipeline und des Bild-Suchers
from infohub.pipeline import run_pipeline
from infohub.retrieval.search_engine import search_images

# 1. VISUELLE BEREINIGUNG: Start ohne Streamlit-Rahmenmenüs
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

# FIX: Verpackung in ein Formular verhindert unerwünschte Re-Triggers bei UI-Klicks
with str_web.form(key="search_form"):
    user_query = str_web.text_input(
        "Stelle eine Frage an dein RAG-System:", 
        placeholder="Z.B. What is the difference between EEU and EEP in Ethiopia?"
    )
    submit_button = str_web.form_submit_button(label="🔍 Suchen")

# 3. INTERNE VERARBEITUNG & DIREKTE AUSGABE
if submit_button and user_query.strip() != "":
    with str_web.spinner("Suche läuft..."):
        try:
            # Führt die Pipeline aus (liefert Antwort, Bild-Metadaten und Phrasen)
            pipeline_result = run_pipeline(user_query)
            
            # Die Antwort erscheint sofort direkt unter der Eingabe
            str_web.markdown("---")
            str_web.info(pipeline_result["answer"])
            
            # -----------------------------------------------------------------
            # 📌 Kontextuelle Abbildung (Aus der lokalen Wissensdatenbank)
            # -----------------------------------------------------------------
            if pipeline_result.get("has_image"):
                str_web.markdown("### 📌 Kontextuelle Abbildung")
                str_web.image(
                    pipeline_result["image_source"],
                    caption=pipeline_result["caption"],
                    use_container_width=True
                )
            
            # -----------------------------------------------------------------
            # 📸 DER VISUELLE REFERENZ-LAYER (Zusätzliche Web-Bilder mit Links)
            # -----------------------------------------------------------------
            optimized_img_query = pipeline_result.get(
                "image_search_phrase", 
                pipeline_result.get("english_query", user_query)
            )
            
            # Holt die strukturierten Bilddaten (Liste von Dicts) aus der Search Engine
            image_results = search_images(optimized_img_query, max_results=3)
            
            if image_results:
                # FIX: Die Überschrift wird jetzt erst gerendert, wenn tatsächlich Bilder existieren!
                str_web.markdown("### 📸 Visuelle Referenzen / Images")
                
                cols = str_web.columns(len(image_results))
                for idx, col in enumerate(cols):
                    item = image_results[idx]
                    
                    # Sicherer Check: Verarbeite strukturiertes Wörterbuch (Dict)
                    if isinstance(item, dict):
                        img_url = item.get("image_url")
                        source_url = item.get("source_url", "#")
                        
                        # Extrahiere die saubere Domain für die Link-Anzeige
                        domain = urlparse(source_url).netloc if source_url != "#" else "Website-Link"
                        
                        if img_url:
                            col.image(img_url, use_container_width=True)
                            col.markdown(f"🔗 [{domain}]({source_url})")
                        else:
                            col.write("Bild nicht verfügbar")
                    
                    # Robuster Fallback, falls doch mal ein reiner URL-String geliefert wird
                    elif isinstance(item, str) and item.startswith("http"):
                        col.image(item, use_container_width=True)
                        col.caption(f"Referenz {idx + 1}")
            else:
                str_web.write("Keine weiteren passenden Referenzbilder im Web gefunden.")
                
        except Exception as e:
            str_web.error(f"Fehler bei der Pipeline-Ausführung: {str(e)}")
