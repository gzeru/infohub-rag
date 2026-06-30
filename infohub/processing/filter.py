def is_meaningful(chunk):

    text = chunk.strip()

    # TOO SHORT
    if len(text) < 120:
        return False

    # TOO MANY NUMBERS
    digit_ratio = sum(c.isdigit() for c in text) / max(len(text), 1)

    if digit_ratio > 0.30:
        return False

    # UI / NAVIGATION WORDS
    noise_keywords = [
        "click",
        "menu",
        "print",
        "fullscreen",
        "toggle",
        "edit",
        "view history",
        "upload file"
    ]

    lowered = text.lower()

    for keyword in noise_keywords:

        if keyword in lowered:
            return False

    return True