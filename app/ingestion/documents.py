from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path
from typing import Any


class InvalidDocumentError(ValueError):
    """Raised when downloaded content is not the declared document type."""


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def clean_text(value: str) -> str:
    value = value.replace("\x00", " ")
    value = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", value)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def text_quality(value: str) -> float:
    if not value:
        return 0.0
    printable = sum(character.isprintable() for character in value) / len(value)
    words = re.findall(r"\w{2,}", value, flags=re.UNICODE)
    replacements = value.count("\ufffd")
    return max(0.0, min(1.0, printable * min(1.0, len(words) / 35) - replacements / 50))


def validate_pdf(content: bytes, max_bytes: int) -> None:
    if not content:
        raise InvalidDocumentError("The PDF response was empty.")
    if len(content) > max_bytes:
        raise InvalidDocumentError("The PDF exceeds the configured size limit.")
    if not content.lstrip().startswith(b"%PDF-"):
        raise InvalidDocumentError("The response is not a PDF file.")
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        if len(reader.pages) < 1:
            raise InvalidDocumentError("The PDF contains no pages.")
    except InvalidDocumentError:
        raise
    except Exception as error:
        raise InvalidDocumentError("The PDF parser rejected this file.") from error


def _ocr_page(pdf_path: Path, page_index: int, languages: list[str]) -> tuple[str, float | None]:
    try:
        import fitz
        import pytesseract
        from PIL import Image

        document = fitz.open(pdf_path)
        page = document.load_page(page_index)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False)
        image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
        language = "+".join(dict.fromkeys(languages or ["eng"]))
        data = pytesseract.image_to_data(
            image,
            lang=language,
            output_type=pytesseract.Output.DICT,
        )
        words = []
        confidences = []
        for word, confidence in zip(data.get("text", []), data.get("conf", [])):
            word = str(word).strip()
            try:
                numeric = float(confidence)
            except (TypeError, ValueError):
                numeric = -1
            if word:
                words.append(word)
            if numeric >= 0:
                confidences.append(numeric)
        confidence = sum(confidences) / len(confidences) if confidences else None
        return clean_text(" ".join(words)), confidence
    except Exception:
        return "", None


def extract_pdf(
    pdf_path: Path,
    *,
    enable_ocr: bool,
    languages: list[str],
) -> list[dict[str, Any]]:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    output = []
    for page_number, page in enumerate(reader.pages, start=1):
        try:
            selectable = clean_text(page.extract_text() or "")
        except Exception:
            selectable = ""
        method = "selectable_text"
        confidence = None
        text = selectable
        if enable_ocr and text_quality(selectable) < 0.28:
            ocr_text, confidence = _ocr_page(pdf_path, page_number - 1, languages)
            if text_quality(ocr_text) > text_quality(selectable):
                text = ocr_text
                method = "ocr"
        output.append({
            "page": page_number,
            "text": text,
            "extraction_method": method,
            "ocr_confidence": confidence,
            "text_quality": round(text_quality(text), 4),
        })
    return output


def extract_plain_text(content: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return clean_text(content.decode(encoding))
        except UnicodeDecodeError:
            continue
    return ""


def extract_docx(content: bytes) -> str:
    try:
        from docx import Document

        document = Document(io.BytesIO(content))
        return clean_text("\n".join(
            paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()
        ))
    except Exception as error:
        raise InvalidDocumentError("The DOCX file could not be extracted.") from error
