import os
import requests


def generate_answer(query: str, retrieved_data: dict) -> str:
    """
    Takes the user query and the structured dictionary of retrieved chunks,
    formats them into a strict RAG prompt, and asks the local Ollama LLM to synthesize an answer.
    """
    # 1. Format the retrieved dictionary chunks into a readable text block for the LLM
    context_str = ""
    for title, chunks in retrieved_data.items():
        context_str += f"Source Document: {title}\n"
        for chunk in chunks:
            context_str += f"- {chunk}\n"
        context_str += "\n"

    if not context_str.strip():
        return "No relevant source context was found to answer this question."

    # 2. Build a strict system prompt to prevent the model from hallucinating
    system_instruction = (
        "You are an expert factual assistant for the InfoHub platform.\n"
        "Your task is to answer the user's query using the provided Source Documents below.\n"
        "Guidelines:\n"
        "1. Prioritize the clear facts mentioned in the provided context if they are helpful.\n"
        "2. If the retrieved context is missing, blocked, or does not contain enough information, do NOT fail. Instead, use your own reliable background knowledge to provide a comprehensive, accurate, and structured answer to the user.\n"
        "3. Keep the tone professional, objective, and helpful.\n"
    )

    full_prompt = f"{system_instruction}\n=== CONTEXT ===\n{context_str}=== QUERY ===\n{query}\n\nAnswer:"

    # 3. Request setup for the LOCAL OLLAMA SERVER
    # We point the engine to your own machine (localhost) instead of Hugging Face
    ollama_url = "http://localhost:11434/api/generate"

    payload = {
        "model": "llama3.2:3b",  # Directing the request to the brain we just pulled
        "prompt": full_prompt,
        "stream": False,  # Return the full answer at once instead of word-by-word
        "options": {
            "temperature": 0.1  # Keep temperature low to enforce factual accuracy
        }
    }

    try:
        # Send the payload to your running background server
        response = requests.post(ollama_url, json=payload, timeout=180)

        if response.status_code != 200:
            return f"[Ollama Status Error {response.status_code}]: The local model engine returned an error."

        result = response.json()

        # Ollama structure puts the text inside the "response" key
        return result.get("response", "").strip()

    except requests.exceptions.ConnectionError:
        return "[Generation Failed]: Could not connect to Ollama. Please make sure the Ollama application is running in your taskbar."
    except Exception as e:
        return f"[Generation Failed]: An unexpected error occurred: {e}"