import re

def split_markdown_sections(markdown_text: str) -> list[dict]:
    """
    Split a markdown document into sections based on '##' headers.

    Docling exports section structure as markdown headers rather than as
    discrete objects, so we recover it here. Text appearing before the first
    header is kept under a "Preamble" section so nothing is lost.

    Returns: [{"title": str, "text": str}, ...]
    """
    # Match lines starting with 2+ '#' followed by a space, capturing the heading text
    pattern = re.compile(r"^#{2,}\s+(.*)$", re.MULTILINE)

    matches = list(pattern.finditer(markdown_text))

    if not matches:
        # No headers found — treat the whole document as one section
        return [{"title": "Document", "text": markdown_text.strip()}]

    sections: list[dict] = []

    # Capture any text before the first header
    preamble = markdown_text[: matches[0].start()].strip()
    if preamble:
        sections.append({"title": "Preamble", "text": preamble})

    for i, match in enumerate(matches):
        title = match.group(1).strip()
        body_start = match.end()
        # Body runs until the next header, or to the end of the document
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown_text)
        body = markdown_text[body_start:body_end].strip()

        if body:  # skip headers with no content under them
            sections.append({"title": title, "text": body})

    return sections