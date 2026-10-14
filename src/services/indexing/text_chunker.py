def chunk_sections(
        sections: list[dict],
        max_words: int = 300,
        overlap: int = 40
) -> list[dict]:
    """
    Split each section's text into overlapping chunks of `max_words` words,
    stepping forward by (max_words - overlap) words each time.

    Returns a list of dicts: {"section_title": str, "text": str, "chunk_index": int}
    """

    if overlap >= max_words:
        raise ValueError("overlap must be less than max_words, or chunks will never advance.")

    step = max_words - overlap
    all_chunks: list[dict] = []

    for section in sections:
        section_title = section.get("title", "")
        text = section.get("text", "") or ""
        words = text.split()

        if not words:
            continue # skip empty sections

        chunk_index = 0
        i = 0
        while i < len(words):
            chunk_word = words[i: i + max_words]
            all_chunks.append({
                "section_title": section_title,
                "text": " ".join(chunk_word),
                "chunk_index": chunk_index
            })
            chunk_index += 1
            i += step

    return all_chunks
