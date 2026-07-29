from unittest.mock import patch

import pytest

from app.ingestion.documents import InvalidDocumentError, extract_pdf, validate_pdf


def test_html_disguised_as_pdf_is_rejected():
    with pytest.raises(InvalidDocumentError):
        validate_pdf(b"<html>not a pdf</html>", 10_000)


def test_empty_pdf_is_rejected():
    with pytest.raises(InvalidDocumentError):
        validate_pdf(b"", 10_000)


def test_ocr_is_optional_and_quality_driven(tmp_path):
    from pypdf import PdfWriter
    path = tmp_path / "scan.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with path.open("wb") as handle:
        writer.write(handle)
    with patch("app.ingestion.documents._ocr_page", return_value=("Reliable extracted words from scan", 88.0)) as ocr:
        records = extract_pdf(path, enable_ocr=True, languages=["en"])
    ocr.assert_called_once()
    assert records[0]["extraction_method"] == "ocr"
    assert records[0]["page"] == 1
