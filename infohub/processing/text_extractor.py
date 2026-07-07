import re
from bs4 import BeautifulSoup

REMOVE_TAGS = [
    "script", "style", "noscript", "header",
    "footer", "nav", "aside", "form", "button"
]

# These are strict UI elements we only want to drop if they appear standalone
REMOVE_KEYWORDS = {
    "main menu", "donate", "create account", "log in",
    "edit", "view history", "search", "appearance",
    "toggle", "contents", "random article", "upload file",
    "jump to navigation", "jump to search"
}

def extract_text(html: str, max_chars: int = 100000) -> str:
    """
    Parses raw HTML, strips away non-content layout elements, and extracts
    clean structural text without accidentally destroying valid prose paragraphs.
    Protected against type errors and huge payload overflows.
    """
    # 1. Defensiver Check gegen unzulässige Datentypen
    if not html or not isinstance(html, str):
        return ""

    # Hard Cap: Text vorab abschneiden, um Speicherüberlastung bei riesigen Dokumenten zu verhindern
    if len(html) > max_chars * 10:  
        html = html[:max_chars * 10]

    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as e:
        print(f"[EXTRACTOR-FEHLER] BeautifulSoup Parsing fehlgeschlagen: {str(e)}")
        return ""

    # 2. Swiftly decompose structural layout clutter
    for element in soup.find_all(REMOVE_TAGS):
        element.decompose()

    # 3. Extract raw text with uniform word spacing
    text = soup.get_text(separator=" ")

    lines = []
    for line in text.splitlines():
        # Whitespaces am Rand entfernen und multiple interne Leerzeichen kollabieren
        line = line.strip()
        line = re.sub(r'\s+', ' ', line)

        if not line:
            continue

        # 4. Handle short lines / UI text meticulously
        if len(line) < 30:
            # Check if this short line is just a stray navigation or layout word
            if line.lower() in REMOVE_KEYWORDS:
                continue
            # Keep short lines if they look like normal content sentences or headings
            if len(line) < 10:
                continue

        # 5. Standalone check: Don't let UI words murder long, valuable sentences
        if line.lower() in REMOVE_KEYWORDS:
            continue

        lines.append(line)

    # 6. Join with structural double newlines to match segmenter patterns
    result_text = "\n\n".join(lines)
    
    # Abschließende Längenbegrenzung für das Token-Sicherheitsnetz
    return result_text[:max_chars]
