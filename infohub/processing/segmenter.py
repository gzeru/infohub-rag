def segment_text(text: str, chunk_size: int = 500):
    """
    Slices raw text into clean chunks based on structural paragraphs,
    preserving internal punctuation and spacing accurately.
    """
    # Split by single or multiple newlines to catch actual paragraph breaks
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

    chunks = []
    current_chunk = []
    current_length = 0

    for para in paragraphs:
        para_len = len(para)

        # If adding this paragraph exceeds our chunk size limit
        if current_length + para_len > chunk_size:
            if current_chunk:
                # Join the accumulated paragraphs with a newline or space
                chunks.append("\n\n".join(current_chunk))

            # Reset and seed the new chunk with the current paragraph
            current_chunk = [para]
            current_length = para_len
        else:
            # Keep the paragraph intact as a complete string
            current_chunk.append(para)
            # Account for the joining character length (e.g., +2 for '\n\n')
            current_length += para_len + 2

    # Don't forget to flush out the final chunk remaining in the buffer
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks