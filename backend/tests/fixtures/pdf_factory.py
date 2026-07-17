from pathlib import Path

from reportlab.pdfgen.canvas import Canvas


def create_test_pdf(
    file_path: Path,
    pages: list[str],
    title: str = "Synthetic Proposal",
    author: str = "Proposal Intelligence Tests",
) -> Path:
    """Create a synthetic PDF for document-parser tests."""

    canvas = Canvas(str(file_path))
    canvas.setTitle(title)
    canvas.setAuthor(author)

    for page_text in pages:
        canvas.drawString(
            72,
            750,
            page_text,
        )
        canvas.showPage()

    canvas.save()

    return file_path
