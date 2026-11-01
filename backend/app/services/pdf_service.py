"""
PDF Service for SanshthaSetu.
Extracts page-by-page text from PDF files using PyMuPDF (fitz).
"""

from __future__ import annotations

import fitz  # PyMuPDF


class PdfService:
    @staticmethod
    def extract_pages_from_bytes(file_bytes: bytes) -> list[tuple[int, str]]:
        """
        Extract page text from raw PDF bytes.
        Returns a list of tuples: (page_number_1_based, page_text).
        """
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages: list[tuple[int, str]] = []
        try:
            for idx, page in enumerate(doc, start=1):
                text = page.get_text() or ""
                pages.append((idx, text))
        finally:
            doc.close()
        return pages

    @staticmethod
    def validate_pdf_bytes(file_bytes: bytes, max_size_mb: int = 25) -> None:
        """
        Validate PDF magic bytes (%PDF) and maximum file size.
        Raises ValueError if validation fails.
        """
        if len(file_bytes) > max_size_mb * 1024 * 1024:
            raise ValueError(f"File exceeds maximum allowed size of {max_size_mb} MB.")

        if not file_bytes.startswith(b"%PDF"):
            raise ValueError("Invalid file format. Uploaded file is not a valid PDF document.")


pdf_service = PdfService()

