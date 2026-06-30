import streamlit as st
from groq import Groq

def generate_answer(context: str, query: str):
    """
    Connects securely to Groq Cloud API using the secret key stored 
    on Streamlit, processing RAG contexts with zero local dependencies.
    """
    # 1. Pull the API key safely from Streamlit Cloud Secrets
    if "GROQ_API_KEY" not in st.secrets:
        return "❌ Error: GROQ_API_KEY is missing from your Streamlit App Secrets."
        
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    
    # 2. Build your secure, clean RAG prompt
    system_prompt = "You are a helpful assistant. Answer the question accurately using ONLY the provided context."
    user_prompt = f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
    
    try:
        # 3. Call the high-speed Llama3 cloud model
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="llama3-8b-8192",  # Free tier eligible, blazingly fast
            temperature=0.3          # Low temperature ensures it sticks to your search context
        )
        return chat_completion.choices[0].message.content

    except Exception as e:
        return f"❌ Cloud Generation Failed: {str(e)}"
