import re
import os
from urllib.parse import urlparse
from tavily import TavilyClient

# Neuer, stabiler Fallback-Import (Standardbibliothek oder leichtgewichtiges Paket)
try:
    from duckduckgo_search import DDGS
    DDG_AVAILABLE = True
except ImportError:
    DDG_AVAILABLE = False


def optimize_query_generically(raw_query: str) -> str:
    """
    Cleans up conversational and filler words from a user prompt
    to make it highly effective for search engines.
    """
    if not raw_query or not isinstance(raw_query, str):
        return ""

    # Convert to lowercase for uniform processing
    clean_query = raw_query.lower()

    # Remove conversational phrases and filler words across English and German
    fillers = [
        r"\bplease tell me about\b", r"\bexplain\b", r"\bshow me\b",
        r"\bwie funktioniert\b", r"\bwas ist\b", r"\bwarum ist\b"
    ]

    for filler in fillers:
        clean_query = re.sub(filler, "", clean_query)

    # Clean up multiple whitespaces left over from removals
    clean_query = " ".join(clean_query.split()).strip()

    # Fallback to the raw query if the cleaning process emptied the string
    return clean_query if clean_query else raw_query


def _fallback_web_search(search_phrase: str, max_results: int) -> list:
    """Kostenloser, stabiler Ausfallschutz über DuckDuckGo, falls Tavily streikt."""
    if not DDG_AVAILABLE:
        print("[WARNUNG] DuckDuckGo-Paket 'duckduckgo_search' nicht installiert. Kein Fallback möglich.")
        return []
    
    print(f"[FALLBACK] Starte Notfall-Suche über DuckDuckGo für: '{search_phrase}'")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(search_phrase, max_results=max_results))
            
        mapped = []
        for item in results:
            url = item.get("href", "")
            if ".m.wikipedia.org" in url:
                url = url.replace(".m.wikipedia.org", ".wikipedia.org")
                
            mapped.append({
                "title": item.get("title", ""),
                "url": url,
                "snippet": item.get("body", "")
            })
        return mapped
    except Exception as e:
        print(f"[CRITICAL] Auch Notfall-Suche über DuckDuckGo fehlgeschlagen: {e}")
        return []


def search(query: str, max_results: int = 2) -> list:
    """
    Holt Suchergebnisse über die Tavily API. 
    Weicht bei Fehlern oder Timeout automatisch auf DuckDuckGo aus.
    """
    search_phrase = optimize_query_generically(query)
    
    # Schlüssel-Sicherheit: Nutze Umgebungsvariable, sonst ein leeres Fallback-Feld statt Hardcoding
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    
    if not TAVILY_API_KEY:
        print("[WARNUNG] Kein TAVILY_API_KEY in Umgebungsvariablen gesetzt. Weiche direkt auf Fallback aus.")
        return _fallback_web_search(search_phrase, max_results)

    print(f"[DEBUG] Sende optimierte Query an Tavily API: '{search_phrase}'")
    raw_mapped_results = []
    
    try:
        client = TavilyClient(api_key=TAVILY_API_KEY)
        response = client.search(
            query=search_phrase, 
            search_depth="basic", 
            max_results=max_results
        )
        
        raw_results = response.get("results", [])
        
        for item in raw_results:
            url = item.get("url", "")
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
        print(f"[ERROR] Tavily Suchaufruf fehlgeschlagen: {e}. Starte automatische Schadensbegrenzung...")
        return _fallback_web_search(search_phrase, max_results)


def search_images(query: str, max_results: int = 3) -> list:
    """
    Sucht nach Bildern über Tavily. Fängt Ausfälle sauber ab.
    """
    search_phrase = optimize_query_generically(query)
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    
    if not TAVILY_API_KEY:
        print("[WARNUNG] Kein TAVILY_API_KEY für Bildersuche vorhanden.")
        return []
    
    structured_images = []
    try:
        client = TavilyClient(api_key=TAVILY_API_KEY)
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
