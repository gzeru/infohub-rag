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


def build_xml_context(results: list) -> str:
    """
    Abstrakte Kapselungsebene: Wandelt die Suchergebnisse in ein striktes 
    XML-Schema um, um syntaktische Barrieren für den Attention-Mechanismus 
    des LLMs zu errichten.
    """
    if not results:
        return "<search_knowledge_base>\n  <!-- Keine Ergebnisse gefunden -->\n</search_knowledge_base>"

    context_elements = ["<search_knowledge_base>"]
    
    for index, item in enumerate(results):
        snippet = item.get("snippet", "").strip()
        title = item.get("title", "").strip()
        url = item.get("url", "").strip()
        
        context_elements.append(f'  <source_node id="{index + 1}">')
        context_elements.append(f"    <metadata>")
        context_elements.append(f"      <title>{title}</title>")
        context_elements.append(f"      <source_url>{url}</source_url>")
        context_elements.append(f"    </metadata>")
        context_elements.append(f"    <raw_fact_stream>\n{snippet}\n    </raw_fact_stream>")
        context_elements.append(f"  </source_node>")
        
    context_elements.append("</search_knowledge_base>")
    return "\n".join(context_elements)


def search(query: str, max_results: int = 2):
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
        
        # JETZT WICHTIG: Wir jagen die Ergebnisse durch die abstrakte XML-Strukturierung
        xml_context = build_xml_context(raw_mapped_results)
        return xml_context

    except Exception as e:
        print(f"[ERROR] Tavily Suchaufruf fehlgeschlagen: {e}")
        return build_xml_context([])
