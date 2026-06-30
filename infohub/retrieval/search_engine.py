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
                # Version-Safe fallback trick:
                # Try the modern 'query' keyword, then 'keywords', then fallback to positional
                try:
                    raw_generator = ddgs.text(query=search_phrase, max_results=max_results)
                except TypeError:
                    try:
                        raw_generator = ddgs.text(keywords=search_phrase, max_results=max_results)
                    except TypeError:
                        raw_generator = ddgs.text(search_phrase, max_results=max_results)

                for item in list(raw_generator):
                    url = item.get("href", item.get("link", ""))
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
                        "url": url
                    })

            if results:
                return results

        except Exception as e:
            print(f"[Attempt {attempt + 1}] Search failed: {e}")
            time.sleep(1)

    return []
