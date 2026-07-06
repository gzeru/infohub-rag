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


def search(query: str, max_results: int = 2) -> list:
    """
    Optimizes the incoming query and retrieves clean search results
    as a raw list of dictionaries using the Tavily API platform.
    """
    # 1. Clean the incoming query using your existing function
    search_phrase = optimize_query_generically(query)
    
    # 2. Add geographic context automatically for infrastructure abbreviations
    if "eeu" in search_phrase or "eep" in search_phrase:
        if "ethiopia" not in search_phrase:
            search_phrase = f"Ethiopia {search_phrase}"

    # 3. Initialize Tavily Client
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "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")
    client = TavilyClient(api_key=TAVILY_API_KEY)

    print(f"[DEBUG] Sende optimierte Query an Tavily API: '{search_phrase}'")
    
    raw_mapped_results = []
    try:
        # Abruf über Tavily
        response = client.search(
            query=search_phrase, 
            search_depth="basic", 
            max_results=max_results
        )
        
        raw_results = response.get("results", [])
        
        for item in raw_results:
            url = item.get("url", "")
            
            # Wikipedia Desktop-Normalisierung beibehalten
            if "en.m.wikipedia.org" in url:
                url = url.replace("en.m.wikipedia.org", "en.wikipedia.org")
                
            raw_mapped_results.append({
                "title": item.get("title", ""),
                "url": url,
                "snippet": item.get("content", "")  
            })
            
        print(f"[DEBUG] API-Abruf erfolgreich! {len(raw_mapped_results)} Ergebnisse geladen.")
        
        # JETZT KORREKT: Direkte Rückgabe der Rohdaten-Liste für die Pipeline
        return raw_mapped_results

    except Exception as e:
        print(f"[ERROR] Tavily Suchaufruf fehlgeschlagen: {e}")
        return []


def search_images(query: str, max_results: int = 3) -> list:
    """
    NEU: Nutzt Tavily, um relevante Bild-URLs passend zur Suchanfrage zu finden.
    Gibt eine saubere Liste von direkten Bild-URLs (Strings) zurück.
    """
    search_phrase = optimize_query_generically(query)
    
    # Geografischen Kontext mitsenden, falls nötig
    if "eeu" in search_phrase or "eep" in search_phrase:
        if "ethiopia" not in search_phrase:
            search_phrase = f"Ethiopia {search_phrase}"
            
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "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")
    client = TavilyClient(api_key=TAVILY_API_KEY)
    
    image_urls = []
    try:
        # Tavily Suche mit aktiviertem Bild-Parameter aufrufen
        response = client.search(
            query=search_phrase,
            search_depth="basic",
            include_images=True,
            max_results=max_results
        )
        
        # Extrahieren der Bilderliste aus dem Antwort-Payload
        raw_images = response.get("images", [])
        
        for img in raw_images:
            # Tavily kann Bilder als Strings oder Dicts zurückgeben. Beides wird hier sicher abgefangen:
            img_url = img.get("url") if isinstance(img, dict) else img
            if img_url and str(img_url).startswith("http"):
                image_urls.append(str(img_url))
                
            if len(image_urls) == max_results:
                break
                
        print(f"[DEBUG] Bildersuche erfolgreich! {len(image_urls)} Bilder geladen.")
    except Exception as e:
        print(f"[ERROR] Tavily Bildersuche fehlgeschlagen: {e}")
        
    return image_urls
