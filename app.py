import streamlit as str_web
import os
import sys

# Interner Systempfad-Abgleich (passiert vollautomatisch im Hintergrund)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Direkter Import der verarbeitenden Pipeline
from infohub.pipeline import run_pipeline

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
            final_answer = run_pipeline(user_query)
            
            # Die Antwort erscheint sofort direkt unter der Eingabe
            str_web.markdown("---")
            str_web.info(final_answer)
            
        except Exception as e:
            str_web.error(f"Fehler: {str(e)}")
