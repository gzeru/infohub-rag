import re
import time
from duckduckgo_search import DDGS


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


def search(query: str, max_results: int = 10, retries: int = 2):
    """
    Optimizes the incoming query and retrieves clean search results
    using a bulletproof, version-safe parameter fallback strategy.
    """
    search_phrase = optimize_query_generically(query)

    for attempt in range(retries):
        results = []
        seen_urls = set()

        try:
            with DDGS() as ddgs:
                # Version-Safe fallback trick
                try:
                    raw_results = ddgs.text(query=search_phrase, max_results=max_results)
                except TypeError:
                    try:
                        raw_results = ddgs.text(keywords=search_phrase, max_results=max_results)
                    except TypeError:
                        raw_results = ddgs.text(search_phrase, max_results=max_results)

                # CRITICAL FIX: If DDGS encounters an error or returns None, skip to next attempt
                if not raw_results:
                    continue

                # Safely iterate over the returned list
                for item in raw_results:
                    if not isinstance(item, dict):
                        continue
                        
                    url = item.get("href", "")
                    if not url:
                        continue

                    # Normalize mobile Wikipedia links to desktop
                    if "en.m.wikipedia.org" in url:
                        url = url.replace("en.m.wikipedia.org", "en.wikipedia.org")

                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    results.append({
                        "title": item.get("title", ""),
                        "url": url,
                        "snippet": item.get("body", "")  # Included for utility
                    })

            if results:
                return results

        except Exception as e:
            print(f"[Attempt {attempt + 1}] Search failed: {e}")
            # Don't sleep on the final attempt
            if attempt < retries - 1:
                time.sleep(1)

    return []
