import re
import os
from urllib.parse import urlparse
from tavily import TavilyClient


def optimize_query_generically(raw_query: str) -> str:
    """
    Cleans up conversational and filler words from a user prompt
    to make it highly effective for search engines.
    """
    # Convert to lowercase for uniform processing
    clean_query = raw_query.lower()

    # Remove conversational phrases and filler words across English and German
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


def search(query: str, max_results: int = 2) -> list:
    """
    Vollkommen generisch: Optimiert die Abfrage und holt Suchergebnisse
    als Liste von Dictionaries über die Tavily API.
    """
    # 1. Clean the incoming query
    search_phrase = optimize_query_generically(query)
    
    # 2. Initialize Tavily Client
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "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")
    client = TavilyClient(api_key=TAVILY_API_KEY)

    print(f"[DEBUG] Sende optimierte Query an Tavily API: '{search_phrase}'")
    
    raw_mapped_results = []
    try:
        response = client.search(
            query=search_phrase, 
            search_depth="basic", 
            max_results=max_results
        )
        
        raw_results = response.get("results", [])
        
        for item in raw_results:
            url = item.get("url", "")
            
            # Wikipedia Desktop-Normalisierung (generisch für alle Sprachen)
            if ".m.wikipedia.org" in url:
                url = url.replace(".m.wikipedia.org", ".wikipedia.org")
                
            raw_mapped_results.append({
                "title": item.get("title", ""),
                "url": url,
                "snippet": item.get("content", "")  
            })
            
        print(f"[DEBUG] API-Abruf erfolgreich! {len(raw_mapped_results)} Ergebnisse geladen.")
        return raw_mapped_results

    except Exception as e:
        print(f"[ERROR] Tavily Suchaufruf fehlgeschlagen: {e}")
        return []


def search_images(query: str, max_results: int = 3) -> list:
    """
    Vollkommen generisch: Sucht nach Bildern und verknüpft sie dynamisch mit den 
    Quell-Websites, ohne jegliche feste Filter oder länderspezifische Begriffe.
    """
    search_phrase = optimize_query_generically(query)
            
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "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")
    client = TavilyClient(api_key=TAVILY_API_KEY)
    
    structured_images = []
    try:
        response = client.search(
            query=search_phrase,
            search_depth="basic",
            include_images=True,
            max_results=max_results
        )
        
        raw_images = response.get("images", [])
        web_results = response.get("results", [])
        
        for idx, img in enumerate(raw_images):
            if isinstance(img, dict):
                img_url = img.get("url")
                img_title = img.get("description", "Image Reference")
            else:
                img_url = str(img)
                img_title = "Image Reference"
                
            if not img_url or not img_url.startswith("http"):
                continue

            # Generische Zuordnung der Quelle: Verknüpfung mit dem Web-Resultat über den Index
            if idx < len(web_results) and isinstance(web_results[idx], dict):
                source_url = web_results[idx].get("url", img_url)
                if img_title == "Image Reference":
                    img_title = web_results[idx].get("title", "Image Reference")
            else:
                source_url = img_url
            
            structured_images.append({
                "image_url": str(img_url),
                "source_url": str(source_url),
                "title": str(img_title)
            })
                
            if len(structured_images) == max_results:
                break
                
        print(f"[DEBUG] Strukturierte Bildersuche erfolgreich! {len(structured_images)} Datensätze geladen.")
    except Exception as e:
        print(f"[ERROR] Tavily Bildersuche fehlgeschlagen: {e}")
        
    return structured_images
