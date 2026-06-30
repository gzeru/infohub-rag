import os
import requests


def generate_answer(query: str, retrieved_data: dict) -> str:
    """
    Takes the user query and the structured dictionary of retrieved chunks,
    formats them into a strict RAG prompt, and asks the LLM to synthesize an answer.
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
        "Your task is to answer the user's query using ONLY the provided Source Documents below.\n"
        "Strict Guidelines:\n"
        "1. Rely strictly on the clear facts mentioned in the context.\n"
        "2. Do not assume, extrapolate, or bring in outside knowledge.\n"
        "3. If the context does not contain the answer, reply exactly with: 'I am sorry, but the retrieved search results do not contain enough information to answer that.'\n"
    )

    full_prompt = f"{system_instruction}\n=== CONTEXT ===\n{context_str}=== QUERY ===\n{query}\n\nAnswer:"

    # 3. Request setup for the Hugging Face Inference API
    hf_token = os.getenv("HF_TOKEN", "")
    headers = {}
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"

    # Using a reliable, fast text-generation model
    model_id = "tiiuae/falcon-7b-instruct"
    api_url = f"https://api-inference.huggingface.co/models/{model_id}"

    payload = {
        "inputs": full_prompt,
        "parameters": {
            "max_new_tokens": 300,
            "temperature": 0.1,  # Keep temperature low to enforce factual accuracy
            "return_full_text": False
        }
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)

        if response.status_code != 200:
            return f"[LLM API Status {response.status_code}]: The model is currently loading or busy. Please try running it again in a few moments."

        result = response.json()

        if isinstance(result, list) and len(result) > 0:
            return result[0].get("generated_text", "").strip()
        elif isinstance(result, dict):
            return result.get("generated_text", "").strip()
        return str(result)

    except Exception as e:
        return f"[Generation Failed]: Could not connect to the LLM backend. Error: {e}"