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

def extract_text(html: str) -> str:
    """
    Parses raw HTML, strips away non-content layout elements, and extracts
    clean structural text without accidentally destroying valid prose paragraphs.
    """
    soup = BeautifulSoup(html, "html.parser")

    # 1. Swiftly decompose structural layout clutter
    for element in soup.find_all(REMOVE_TAGS):
        element.decompose()

    # 2. Extract raw text with uniform word spacing
    text = soup.get_text(separator=" ")

    lines = []
    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        # 3. Handle short lines / UI text meticulously
        if len(line) < 30:
            # Check if this short line is just a stray navigation or layout word
            if line.lower() in REMOVE_KEYWORDS:
                continue
            # Keep short lines if they look like normal content sentences or headings
            if len(line) < 10:
                continue

        # 4. Standalone check: Don't let UI words murder long, valuable sentences
        if line.lower() in REMOVE_KEYWORDS:
            continue

        lines.append(line)

    # 5. Join with structural double newlines to match segmenter patterns
    return "\n\n".join(lines)