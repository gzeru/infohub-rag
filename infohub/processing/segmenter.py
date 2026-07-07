import re

def _split_oversized_paragraph(para: str, max_size: int) -> list:
    """
    Sicherheitsnetz: Zerlegt einen einzelnen, übergroßen Absatz bevorzugt 
    an Satzzeichen (. ! ?), alternativ an Wortgrenzen, damit kein Chunk
    die max_size überschreitet.
    """
    # Versuch, an Sätzen zu trennen (schaut nach . ! ? gefolgt von einem Leerzeichen)
    sentences = re.split(r'(?<=[.!?])\s+', para)
    
    sub_chunks = []
    current_sub = []
    current_len = 0
    
    for sentence in sentences:
        sent_len = len(sentence)
        
        # Wenn selbst ein einzelner Satz zu lang ist, trennen wir ihn hart an Wortgrenzen
        if sent_len > max_size:
            if current_sub:
                sub_chunks.append(" ".join(current_sub))
                current_sub = []
                current_len = 0
            
            # Trennung nach Wörtern
            words = sentence.split(" ")
            for word in words:
                if current_len + len(word) + 1 > max_size:
                    if current_sub:
                        sub_chunks.append(" ".join(current_sub))
                    current_sub = [word]
                    current_len = len(word)
                else:
                    current_sub.append(word)
                    current_len += len(word) + 1
            continue

        if current_len + sent_len + 1 > max_size:
            if current_sub:
                sub_chunks.append(" ".join(current_sub))
            current_sub = [sentence]
            current_len = sent_len
        else:
            current_sub.append(sentence)
            current_len += sent_len + 1
            
    if current_sub:
        sub_chunks.append(" ".join(current_sub))
        
    return sub_chunks


def segment_text(text: str, chunk_size: int = 500) -> list:
    """
    Slices raw text into clean chunks based on structural paragraphs.
    Guarantees that no chunk exceeds chunk_size, even if raw data 
    contains oversized monolithic paragraphs.
    """
    if not text or not isinstance(text, str):
        return []

    # Split by single or multiple newlines to catch actual paragraph breaks
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

    chunks = []
    current_chunk = []
    current_length = 0

    for para in paragraphs:
        para_len = len(para)

        # Überprüfung, ob dieser Absatz isoliert die chunk_size sprengt
        if para_len > chunk_size:
            # 1. Vorherigen Buffer leeren, falls vorhanden
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_length = 0
            
            # 2. Den Riesen-Absatz kontrolliert zerlegen
            sub_sections = _split_oversized_paragraph(para, chunk_size)
            chunks.extend(sub_sections)
            continue

        # Normaler Akkumulations-Pfad für regelkonforme Absätze
        if current_length + para_len > chunk_size:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))

            current_chunk = [para]
            current_length = para_len
        else:
            current_chunk.append(para)
            # Berücksichtigung des Trennzeichens (+2 für '\n\n')
            current_length += para_len + 2

    # Letzten verbleibenden Rest ausgeben
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks
