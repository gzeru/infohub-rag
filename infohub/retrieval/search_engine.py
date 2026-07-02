import re
import os
from tavily import TavilyClient


def optimize_query_generically(raw_query: str) -> str:
    """
    Cleans up conversational and filler words from a user prompt
    to make it highly effective for search engines.
    """
    # Convert to lowercase for uniform processing
    clean_query = raw_query.lower()

    # Remove conversational phrases and filler words across English and German
    # Added word boundaries to 'work' and 'works' to prevent mangling words like 'network'
    fillers = [
        r"\bhow does\b", r"\bwhy is\b", r"\bwhat is\b", r"\bplease tell me about\b",
        r"\bworks\b", r"\bwork\b", r"\bexplain\b", r"\bshow me\b", r"\bthe\b",
        r"\ba\b", r"\ban\b", r"\bis\b", r"\bdoes\b", r"\bdo\b",
        r"\bwie funktioniert\b", r"\bwas ist\b", r"\bwarum ist\b"
    ]

    for filler in fillers:
        clean_query = re.sub(filler, "", clean_query)

    # Clean up multiple whitespaces left over from removals
    clean_query = " ".join(clean_query.split()).strip()

    # Fallback to the raw query if the cleaning process emptied the string
    return clean_query if clean_query else raw_query


def search(query: str, max_results: int = 5):
    """
    Optimizes the incoming query and retrieves clean search results
    using the stable, RAG-optimized Tavily API platform.
    """
    # 1. Clean the incoming query using your existing function
    search_phrase = optimize_query_generically(query)
    
    # 2. Add geographic context automatically for infrastructure abbreviations
    if "eeu" in search_phrase or "eep" in search_phrase:
        if "ethiopia" not in search_phrase:
            search_phrase = f"Ethiopia {search_phrase}"

    # 3. Initialize Tavily Client (Replace placeholder with your actual key if not using env vars)
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "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")
    client = TavilyClient(api_key=TAVILY_API_KEY)

    print(f"[DEBUG] Sende optimierte Query an Tavily API: '{search_phrase}'")
    
    results = []
    try:
        # Abruf über Tavily
        response = client.search(
            query=search_phrase, 
            search_depth="basic", 
            max_results=max_results
        )
        
        raw_results = response.get("results", [])
        
        # Mapping der Feldnamen, damit der Rest deiner Pipeline unverändert bleibt
        for item in raw_results:
            url = item.get("url", "")
            
            # Wikipedia Desktop-Normalisierung beibehalten
            if "en.m.wikipedia.org" in url:
                url = url.replace("en.m.wikipedia.org", "en.wikipedia.org")
                
            results.append({
                "title": item.get("title", ""),
                "url": url,
                "snippet": item.get("content", "")  # Tavily liefert den bereinigten Text in 'content'
            })
            
        print(f"[DEBUG] Pipeline erfolgreich! {len(results)} Ergebnisse extrahiert.")
        return results

    except Exception as e:
        print(f"[ERROR] Tavily Suchaufruf fehlgeschlagen: {e}")
        return []
