import logging
import os
import shutil
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

import pdfplumber
import pytesseract
from PIL import Image
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFInfoNotInstalledError

from app.core.config import settings
from app.services.text_cleaner import clean_vietnamese_text

logger = logging.getLogger("uvicorn.error")

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
COMMON_TESSERACT_PATHS = (
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
)
COMMON_POPPLER_DIRS = (
    Path(r"C:\Program Files\poppler\Library\bin"),
    Path(r"C:\Program Files\poppler\bin"),
    Path.home() / "scoop" / "apps" / "poppler" / "current" / "bin",
)
WINGET_POPPLER_ROOT = (
    Path.home()
    / "AppData"
    / "Local"
    / "Microsoft"
    / "WinGet"
    / "Packages"
)


def _extract_zip_xml_text(path: str, *, prefixes: tuple[str, ...]) -> str:
    chunks: list[str] = []
    with ZipFile(path) as archive:
        file_names = sorted(
            name
            for name in archive.namelist()
            if any(name.startswith(prefix) for prefix in prefixes)
            and name.endswith(".xml")
        )
        for file_name in file_names:
            root = ElementTree.fromstring(archive.read(file_name))
            chunks.extend(
                node.text.strip()
                for node in root.iter()
                if node.text and node.text.strip()
            )
    return clean_vietnamese_text("\n".join(chunks))


def _has_meaningful_text(text: str, *, min_alnum_chars: int = 20) -> bool:
    if not text.strip():
        return False
    return sum(char.isalnum() for char in text) >= min_alnum_chars


def _configure_tesseract() -> str | None:
    candidates: list[str] = []
    if settings.TESSERACT_CMD:
        candidates.append(settings.TESSERACT_CMD)

    current_value = getattr(pytesseract.pytesseract, "tesseract_cmd", None)
    if current_value:
        candidates.append(str(current_value))

    resolved_from_path = shutil.which("tesseract")
    if resolved_from_path:
        candidates.append(resolved_from_path)

    candidates.extend(str(path) for path in COMMON_TESSERACT_PATHS)

    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            pytesseract.pytesseract.tesseract_cmd = candidate
            return candidate

    logger.warning("Tesseract executable was not found for OCR extraction")
    return None


def _iter_poppler_candidates() -> list[str | None]:
    candidates: list[str | None] = []

    if settings.POPPLER_PATH:
        candidates.append(settings.POPPLER_PATH)

    for path in os.environ.get("PATH", "").split(os.pathsep):
        normalized = path.strip().strip('"')
        if normalized and ("poppler" in normalized.lower() or "winget" in normalized.lower()):
            candidates.append(normalized)

    for path in COMMON_POPPLER_DIRS:
        candidates.append(str(path))

    try:
        for package_dir in WINGET_POPPLER_ROOT.glob("oschwartz10612.Poppler_*"):
            for extracted_dir in package_dir.glob("poppler-*"):
                candidates.append(str(extracted_dir / "Library" / "bin"))
                candidates.append(str(extracted_dir / "bin"))
    except OSError as exc:
        logger.warning("Could not enumerate WinGet Poppler directories: %s", exc)

    candidates.append(None)

    seen: set[str | None] = set()
    ordered_candidates: list[str | None] = []
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        ordered_candidates.append(candidate)
    return ordered_candidates


def _ocr_image(image: Image.Image) -> str:
    prepared_image = image.convert("L")
    prepared_image = prepared_image.resize(
        (prepared_image.width * 2, prepared_image.height * 2)
    )
    return pytesseract.image_to_string(
        prepared_image,
        lang=settings.OCR_LANGS,
        config="--psm 6",
    )


def _extract_text_from_web(url: str) -> str:
    import requests
    from bs4 import BeautifulSoup

    response = requests.get(url, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    return clean_vietnamese_text(soup.get_text(" ", strip=True))


def _extract_text_from_pdf_layer(file_path: str) -> str:
    try:
        text_chunks: list[str] = []
        with open(file_path, "rb") as file_obj:
            reader = PdfReader(file_obj)
            for page in reader.pages:
                text_chunks.append(page.extract_text() or "")
        return clean_vietnamese_text(
            "\n".join(chunk for chunk in text_chunks if chunk.strip())
        )
    except Exception as exc:
        logger.warning(
            "PyPDF2 failed while extracting PDF text. file=%s error_type=%s error=%s",
            file_path,
            type(exc).__name__,
            exc,
        )
        return ""


def extract_text_pdf(file_path: str) -> str:
    try:
        with pdfplumber.open(file_path) as pdf:
            return clean_vietnamese_text(
                "\n".join(
                    page_text
                    for page in pdf.pages
                    if (page_text := page.extract_text())
                )
            )
    except Exception as exc:
        logger.warning(
            "pdfplumber failed while extracting PDF text. file=%s error_type=%s error=%s",
            file_path,
            type(exc).__name__,
            exc,
        )
        return ""


def extract_text_with_ocr(file_path: str) -> str:
    file_suffix = Path(file_path).suffix.lower()
    if not _configure_tesseract():
        return ""

    try:
        if file_suffix in IMAGE_EXTENSIONS:
            with Image.open(file_path) as image:
                return clean_vietnamese_text(_ocr_image(image))

        for poppler_path in _iter_poppler_candidates():
            try:
                convert_kwargs = {"dpi": settings.OCR_PDF_DPI}
                if poppler_path:
                    convert_kwargs["poppler_path"] = poppler_path

                images = convert_from_path(file_path, **convert_kwargs)
                extracted = [
                    page_text.strip()
                    for image in images
                    if (page_text := _ocr_image(image))
                ]
                text = clean_vietnamese_text(
                    "\n".join(chunk for chunk in extracted if chunk)
                )
                if text.strip():
                    return text
            except PDFInfoNotInstalledError as exc:
                logger.warning(
                    "Poppler candidate failed for OCR. file=%s poppler_path=%s error=%s",
                    file_path,
                    poppler_path,
                    exc,
                )
            except Exception as exc:
                logger.warning(
                    "OCR conversion failed. file=%s poppler_path=%s error_type=%s error=%s",
                    file_path,
                    poppler_path,
                    type(exc).__name__,
                    exc,
                )
    except Exception as exc:
        logger.warning(
            "OCR extraction failed. file=%s error_type=%s error=%s",
            file_path,
            type(exc).__name__,
            exc,
        )

    return ""


def extract_text(path_or_url: str) -> str:
    lower_path = path_or_url.lower()

    if lower_path.startswith("http://") or lower_path.startswith("https://"):
        return _extract_text_from_web(path_or_url)

    if lower_path.endswith(".txt"):
        with open(path_or_url, encoding="utf-8") as file_obj:
            return clean_vietnamese_text(file_obj.read())

    if lower_path.endswith(".pdf"):
        direct_text = _extract_text_from_pdf_layer(path_or_url)
        if _has_meaningful_text(direct_text):
            return direct_text

        plumber_text = extract_text_pdf(path_or_url)
        if _has_meaningful_text(plumber_text):
            return plumber_text

        return extract_text_with_ocr(path_or_url)

    if lower_path.endswith(".docx"):
        return _extract_zip_xml_text(path_or_url, prefixes=("word/",))

    if lower_path.endswith(".pptx"):
        return _extract_zip_xml_text(path_or_url, prefixes=("ppt/slides/",))

    if Path(path_or_url).suffix.lower() in IMAGE_EXTENSIONS:
        return extract_text_with_ocr(path_or_url)

    return ""
