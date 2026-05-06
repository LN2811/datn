import json
import logging
import re
from json import JSONDecodeError
import unicodedata
from groq import Groq

from app.core.config import settings
from app.services.text_cleaner import clean_vietnamese_text

DEFAULT_MODEL_NAME = "llama-3.1-8b-instant"
DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant that provides information based on the given prompt."
)
OUTLINE_CONTEXT_CHARS = 9000
LESSON_CONTEXT_CHARS = 24000
OUTLINE_BATCH_CHARS = 1800
LESSON_BATCH_CHARS = 2600
OUTLINE_MAX_BATCHES = 4
LESSON_MAX_BATCHES = 8
OUTLINE_CHUNK_COMPLETION_TOKENS = 220
OUTLINE_FINAL_COMPLETION_TOKENS = 420
LESSON_CHUNK_COMPLETION_TOKENS = 420
LESSON_FINAL_COMPLETION_TOKENS = 1800
PASSAGE_CHUNK_CHARS = 1400
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "into",
    "your",
    "have",
    "will",
    "when",
    "what",
    "where",
    "which",
    "while",
    "about",
    "them",
    "they",
    "their",
    "there",
    "you",
    "are",
    "was",
    "were",
    "been",
    "using",
    "use",
    "used",
    "can",
    "may",
    "should",
    "how",
    "why",
    "not",
    "all",
    "any",
    "more",
    "less",
    "very",
    "muc",
    "noi",
    "dung",
    "bai",
    "hoc",
    "cho",
    "mot",
    "nhung",
    "nhung",
    "voi",
    "cua",
    "trong",
    "theo",
    "sau",
    "tren",
    "duoc",
    "dang",
    "neu",
    "tu",
    "tai",
    "lieu",
    "phan",
    "cac",
    "can",
    "nen",
    "khong",
    "day",
    "bao",
    "gom",
    "hay",
    "lam",
    "sao",
    "giup",
    "chi",
    "tiet",
    "tong",
    "quan",
    "module",
    "curriculum",
    "title",
    "overview",
    "description",
}
logger = logging.getLogger("uvicorn.error")


class AIResponseFormatError(RuntimeError):
    pass

def _legacy_clean_text(text: str) -> str:
    text = clean_learning_material_text(text)
    text = re.sub(r"(GIÁO TRÌNH.*?\n)+", "", text)
    text = re.sub(r"^\s*\d{1,3}\s*$", "", text, flags=re.MULTILINE)
    text= re.sub(r"\n{2,}","\n\n", text)
    return text.strip()


MAX_TOC_MODULES = 12
TOC_SCAN_LINE_LIMIT = 260
TOC_ENTRY_LINE_LIMIT = 240
SKIPPED_TOC_TITLE_KEYWORDS = {
    "muc luc",
    "table of contents",
    "contents",
    "danh muc",
    "danh sach hinh",
    "danh sach bang",
    "loi noi dau",
    "loi cam on",
    "tai lieu tham khao",
    "references",
    "bibliography",
    "phu luc",
    "appendix",
}


def _fold_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value or "")
    without_marks = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    return without_marks.lower()


def _compact_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _fold_text(value)).strip()


def _line_alnum_ratio(line: str) -> float:
    stripped = line.strip()
    if not stripped:
        return 0
    return sum(char.isalnum() for char in stripped) / max(len(stripped), 1)


def _is_noise_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False

    folded = _compact_key(stripped)
    if re.fullmatch(r"\d{1,4}", stripped):
        return True
    if re.fullmatch(r"[\d\s\.\-/\\_|]+", stripped):
        return True
    if re.fullmatch(r"(page|trang)\s+\d{1,4}", folded):
        return True
    if re.fullmatch(r"(https?://|www\.)\S+", stripped, flags=re.IGNORECASE):
        return True
    if len(stripped) <= 3 and _line_alnum_ratio(stripped) < 0.5:
        return True
    if len(stripped) >= 6 and _line_alnum_ratio(stripped) < 0.22:
        return True
    return False


VIETNAMESE_VOWELS = set(
    "aáàảãạăắằẳẵặâấầẩẫậ"
    "eéèẻẽẹêếềểễệ"
    "iíìỉĩị"
    "oóòỏõọôốồổỗộơớờởỡợ"
    "uúùủũụưứừửữự"
    "yýỳỷỹỵ"
    "AÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬ"
    "EÉÈẺẼẸÊẾỀỂỄỆ"
    "IÍÌỈĨỊ"
    "OÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢ"
    "UÚÙỦŨỤƯỨỪỬỮỰ"
    "YÝỲỶỸỴ"
)
VIETNAMESE_FINAL_SINGLE_CONSONANTS = {"c", "m", "n", "p", "t"}
VIETNAMESE_FINAL_CONSONANT_PAIRS = {"ch", "ng", "nh"}
OCR_SPLIT_LETTER_RUN_RE = re.compile(
    r"(?<!\w)(?:[^\W\d_]\s+){3,}[^\W\d_](?!\w)",
    flags=re.UNICODE,
)


def _has_vietnamese_mark(value: str) -> bool:
    normalized = unicodedata.normalize("NFD", value)
    return "đ" in value.lower() or any(
        unicodedata.category(char) == "Mn" for char in normalized
    )


def _is_vietnamese_vowel(char: str) -> bool:
    return char in VIETNAMESE_VOWELS


def _trailing_vietnamese_consonants(value: str) -> str:
    trailing: list[str] = []
    for char in reversed(value):
        if _is_vietnamese_vowel(char):
            break
        trailing.append(char.lower())
    return "".join(reversed(trailing))


def _split_vietnamese_syllables(value: str) -> list[str]:
    syllables: list[str] = []
    current = ""
    for char in value:
        if not char.isalpha():
            if current:
                syllables.append(current)
                current = ""
            continue

        if current and any(_is_vietnamese_vowel(item) for item in current):
            trailing = _trailing_vietnamese_consonants(current)
            lower_char = char.lower()
            if _is_vietnamese_vowel(char):
                if trailing:
                    syllables.append(current)
                    current = char
                    continue
            elif not trailing:
                if lower_char not in VIETNAMESE_FINAL_SINGLE_CONSONANTS:
                    syllables.append(current)
                    current = char
                    continue
            elif len(trailing) == 1:
                if trailing + lower_char not in VIETNAMESE_FINAL_CONSONANT_PAIRS:
                    syllables.append(current)
                    current = char
                    continue
            else:
                syllables.append(current)
                current = char
                continue

        current += char

    if current:
        syllables.append(current)
    return syllables


def _fix_ocr_split_letters(line: str) -> str:
    if re.search(r"[=<>*/\\^±×÷∑√∞]", line):
        return line

    def _replace_letter_run(match: re.Match[str]) -> str:
        value = match.group(0)
        letters = re.findall(r"[^\W\d_]", value, flags=re.UNICODE)
        if len(letters) < 5 or not _has_vietnamese_mark(value):
            return value

        # OCR/PDF extraction can add spaces between glyphs inside a syllable,
        # especially for Vietnamese characters stored as separate positioned text.
        joined = re.sub(r"(?<=\w)\s+(?=\w)", "", value)
        syllables = _split_vietnamese_syllables(joined)
        if len(syllables) <= 1:
            return joined

        # Remove spaces between split letters, then restore syllable spaces so
        # real Vietnamese words stay readable instead of becoming one long token.
        return " ".join(syllables)

    return OCR_SPLIT_LETTER_RUN_RE.sub(_replace_letter_run, line)


def clean_learning_material_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "")
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x0c", "\n")
    text = re.sub(r"[\x00-\x08\x0b\x0e-\x1f]", " ", text)
    text = clean_vietnamese_text(text)
    text = re.sub(
        r"([A-Za-zÀ-ỹ])-\s*\n\s*([A-Za-zÀ-ỹ])",
        r"\1\2",
        text,
    )
    text = "\n".join(_fix_ocr_split_letters(line) for line in text.splitlines())
    text = clean_vietnamese_text(text)
    text = unicodedata.normalize("NFC", text)

    raw_lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    line_counts: dict[str, int] = {}
    for line in raw_lines:
        key = _compact_key(line)
        if 3 <= len(key) <= 100:
            line_counts[key] = line_counts.get(key, 0) + 1

    cleaned_lines: list[str] = []
    previous_blank = False
    for line in raw_lines:
        if not line:
            if cleaned_lines and not previous_blank:
                cleaned_lines.append("")
            previous_blank = True
            continue

        key = _compact_key(line)
        if line_counts.get(key, 0) >= 4 and len(key) <= 100:
            continue
        if _is_noise_line(line):
            continue

        line = re.sub(r"\s+", " ", line).strip()
        line = re.sub(r"\s+([,.;:!?])", r"\1", line)
        line = re.sub(r"([([{])\s+", r"\1", line)
        cleaned_lines.append(line)
        previous_blank = False

    cleaned = "\n".join(cleaned_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = unicodedata.normalize("NFC", cleaned)
    return cleaned.strip()


def clean_text_v2(text: str) -> str:
    return clean_learning_material_text(text)


def _looks_like_toc_heading(line: str) -> bool:
    key = _compact_key(line)
    return key in {"muc luc", "table of contents", "contents"}


def _clean_toc_title(title: str, *, remove_page_tail: bool) -> str:
    cleaned = re.sub(r"\s*\.{2,}\s*\d{1,4}\s*$", "", title).strip()
    cleaned = re.sub(r"\s*\.{2,}.*$", "", cleaned).strip()
    if remove_page_tail:
        cleaned = re.sub(r"\s+\d{1,4}\s*$", "", cleaned).strip()
    cleaned = re.sub(r"^[\.\-–—:)\s]+", "", cleaned)
    cleaned = re.sub(r"[\.\-–—:\s]+$", "", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _toc_level(number: str) -> int:
    normalized = _compact_key(number)
    if normalized.startswith(("chuong ", "chapter ", "bai ", "phan ")):
        return 1
    numeric = re.search(r"\d+(?:\.\d+)*", number)
    if numeric:
        return numeric.group(0).count(".") + 1
    return 1


def _parse_toc_entry(line: str) -> dict | None:
    original = re.sub(r"\s+", " ", line.strip())
    if not original or _looks_like_toc_heading(original):
        return None

    has_page_tail = bool(
        re.search(r"(?:\.{2,}|\s{2,})\s*\d{1,4}\s*$", line)
    )
    body = re.sub(r"\s*\.{2,}\s*\d{1,4}\s*$", "", original).strip()
    body = re.sub(r"\s{2,}\d{1,4}\s*$", "", body).strip()

    patterns = (
        r"^(?P<number>\d+(?:\.\d+){0,5})(?:[\.)])?\s+(?P<title>.+)$",
        r"^(?P<number>(?:chương|chuong|chapter|bài|bai|phần|phan)\s+[ivxlcdm\d]+)(?:\s*[\.:–—-]\s*|\s+)(?P<title>.+)$",
        r"^(?P<number>[IVXLCDM]+)[\.\)]\s+(?P<title>.+)$",
    )

    parsed: re.Match[str] | None = None
    for pattern in patterns:
        parsed = re.match(pattern, body, flags=re.IGNORECASE)
        if parsed:
            break
    if not parsed:
        return None

    number = parsed.group("number").strip()
    title = _clean_toc_title(
        parsed.group("title"),
        remove_page_tail=has_page_tail,
    )
    title_key = _compact_key(title)
    if not title_key or len(title) < 4 or len(title) > 140:
        return None
    if any(keyword in title_key for keyword in SKIPPED_TOC_TITLE_KEYWORDS):
        return None
    if sum(char.isalpha() for char in title) < 3:
        return None

    return {
        "number": number,
        "title": title,
        "level": _toc_level(number),
        "has_page_tail": has_page_tail,
    }


def _read_toc_entries_from(lines: list[str], start_index: int) -> tuple[list[dict], int]:
    entries: list[dict] = []
    last_entry_index = start_index
    misses = 0
    max_index = min(len(lines), start_index + TOC_ENTRY_LINE_LIMIT)

    for index in range(start_index + 1, max_index):
        parsed = _parse_toc_entry(lines[index])
        if parsed:
            page_tail_entries = sum(1 for entry in entries if entry.get("has_page_tail"))
            if entries and page_tail_entries >= 2 and not parsed.get("has_page_tail"):
                break
            if len(entries) >= 3 and page_tail_entries == 0 and misses > 0:
                break
            parsed["line_index"] = index
            entries.append(parsed)
            last_entry_index = index
            misses = 0
            continue

        if entries:
            misses += 1
            if misses >= 8 and len(entries) >= 3:
                break

    return entries, min(last_entry_index + 1, len(lines))


def _find_toc_entries(cleaned_text: str) -> tuple[list[dict], int]:
    lines = cleaned_text.splitlines()
    for index, line in enumerate(lines[:TOC_SCAN_LINE_LIMIT]):
        if _looks_like_toc_heading(line):
            entries, end_index = _read_toc_entries_from(lines, index)
            if len(entries) >= 2:
                return entries, end_index

    best_entries: list[dict] = []
    best_end_index = 0
    for start_index in range(min(len(lines), TOC_SCAN_LINE_LIMIT)):
        entries, end_index = _read_toc_entries_from(lines, start_index - 1)
        if len(entries) > len(best_entries) and sum(
            1 for entry in entries if entry.get("has_page_tail")
        ) >= 2:
            best_entries = entries
            best_end_index = end_index
        if len(best_entries) >= 4:
            break

    return best_entries, best_end_index


def _dedupe_toc_entries(entries: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    seen: set[str] = set()
    for entry in entries:
        key = _compact_key(f"{entry.get('number', '')} {entry.get('title', '')}")
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    return deduped


def _select_toc_modules(entries: list[dict]) -> list[dict]:
    entries = _dedupe_toc_entries(entries)
    if not entries:
        return []

    level_one = [entry for entry in entries if entry["level"] == 1]
    if len(level_one) >= 2:
        return level_one[:MAX_TOC_MODULES]

    level_two_or_above = [entry for entry in entries if entry["level"] <= 2]
    if len(level_two_or_above) >= 2:
        return level_two_or_above[:MAX_TOC_MODULES]

    return entries[:MAX_TOC_MODULES]


def _infer_curriculum_title(cleaned_text: str) -> str:
    for line in cleaned_text.splitlines()[:40]:
        line_key = _compact_key(line)
        if not line_key or _looks_like_toc_heading(line):
            continue
        if any(keyword in line_key for keyword in SKIPPED_TOC_TITLE_KEYWORDS):
            continue
        if 8 <= len(line) <= 120 and sum(char.isalpha() for char in line) >= 5:
            return line
    return "Curriculum tu muc luc tai lieu"


def extract_curriculum_outline_from_toc(text: str) -> dict | None:
    cleaned_text = clean_learning_material_text(text)
    entries, _ = _find_toc_entries(cleaned_text)
    modules = _select_toc_modules(entries)
    if not modules:
        return None

    module_items: list[dict] = []
    for entry in modules:
        description = f"Muc luc {entry['number']}: {entry['title']}"
        source_description = build_module_source_description(
            text=cleaned_text,
            module_title=entry["title"],
            module_description=description,
        )
        if source_description and source_description != description:
            description = f"{description}\n\n{source_description}"
        module_items.append(
            {
                "title": entry["title"],
                "description": description,
                "toc_number": entry["number"],
            }
        )

    return {
        "title": _infer_curriculum_title(cleaned_text),
        "overview": "Curriculum duoc tao tu muc luc trong tai lieu goc sau khi lam sach du lieu.",
        "modules": module_items,
    }


def _strip_code_fences(content: str) -> str:
    cleaned = (content or "").strip()
    if not cleaned.startswith("```"):
        return cleaned

    lines = cleaned.splitlines()
    if not lines:
        return ""

    first_line = lines[0].strip().lower()
    if first_line.startswith("```"):
        lines = lines[1:]

    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]

    if lines and lines[0].strip().lower() == "json":
        lines = lines[1:]

    return "\n".join(lines).strip()


def _truncate_preview(content: str, *, limit: int = 240) -> str:
    cleaned = " ".join((content or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit]}..."


def _normalize_block(block: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in block.splitlines()]
    return "\n".join(line for line in lines if line).strip()

def format_readable_paragraphs(
    text: str,
    *,
    max_sentences_per_paragraph: int = 3,
) -> str:
    if not text:
        return ""

    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if not text:
        return ""

    # Nếu text đã có đoạn rõ bằng dòng trống thì chỉ làm sạch từng đoạn, không phá bố cục.
    if "\n\n" in text:
        paragraphs = [
            re.sub(r"\s+", " ", paragraph).strip()
            for paragraph in re.split(r"\n\s*\n+", text)
            if paragraph.strip()
        ]
        return "\n\n".join(paragraphs)

    # Tách câu theo dấu kết thúc câu.
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?。！？])\s+", text)
        if sentence.strip()
    ]

    if len(sentences) <= max_sentences_per_paragraph:
        return " ".join(sentences)

    paragraphs: list[str] = []
    current: list[str] = []

    for sentence in sentences:
        current.append(sentence)

        if len(current) >= max_sentences_per_paragraph:
            paragraphs.append(" ".join(current))
            current = []

    if current:
        paragraphs.append(" ".join(current))

    return "\n\n".join(paragraphs)


def _is_useful_passage(passage: str) -> bool:
    lines = [line.strip() for line in passage.splitlines() if line.strip()]
    if not lines:
        return False

    if all(_looks_like_toc_heading(line) for line in lines):
        return False
    if _looks_like_toc_heading(lines[0]) and len(lines) > 1:
        toc_lines = lines[1:]
        if all(
            (entry := _parse_toc_entry(line)) is not None and entry.get("has_page_tail")
            for line in toc_lines
        ):
            return False
    if all(_is_noise_line(line) for line in lines):
        return False
    if all(
        (entry := _parse_toc_entry(line)) is not None and entry.get("has_page_tail")
        for line in lines
    ):
        return False

    normalized = _normalize_block(passage)
    compact = _compact_key(normalized)
    if len(compact) < 12 and not any(_parse_toc_entry(line) for line in lines):
        return False
    if len(normalized) >= 10 and _line_alnum_ratio(normalized) < 0.35:
        return False
    return True


def _chunk_text(text: str, *, max_chars: int = PASSAGE_CHUNK_CHARS) -> list[str]:
    normalized = _normalize_block(text)
    if not normalized:
        return []
    if len(normalized) <= max_chars:
        return [normalized]

    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[\.\!\?\:\;])\s+|\n+", normalized)
        if sentence.strip()
    ]
    if not sentences:
        return [normalized[index : index + max_chars].strip() for index in range(0, len(normalized), max_chars)]

    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current)
        if len(sentence) <= max_chars:
            current = sentence
            continue

        chunks.extend(
            sentence[index : index + max_chars].strip()
            for index in range(0, len(sentence), max_chars)
            if sentence[index : index + max_chars].strip()
        )
        current = ""

    if current:
        chunks.append(current)

    return chunks


def _split_passages(text: str) -> list[str]:
    normalized = clean_learning_material_text(text)
    if not normalized:
        return []

    raw_blocks = [
        block.strip()
        for block in re.split(r"\n\s*\n+", normalized)
        if block.strip()
    ]
    if not raw_blocks:
        raw_blocks = [normalized]

    passages: list[str] = []
    for block in raw_blocks:
        for chunk in _chunk_text(block):
            if _is_useful_passage(chunk):
                passages.append(chunk)
    return passages


def _extract_keywords(*parts: str, limit: int = 16) -> list[str]:
    seen: set[str] = set()
    keywords: list[str] = []
    combined = " ".join(part for part in parts if part).lower()
    for token in re.findall(r"[a-z0-9\u00c0-\u1ef9_+#\.-]{3,}", combined):
        if token in STOPWORDS or token.isdigit() or token in seen:
            continue
        seen.add(token)
        keywords.append(token)
        if len(keywords) >= limit:
            break
    return keywords


def _score_passage(passage: str, keywords: list[str]) -> int:
    lowered = passage.lower()
    score = 0
    for keyword in keywords:
        count = lowered.count(keyword)
        if count:
            score += count * max(len(keyword), 3)
    return score


def _pick_evenly_spaced_indices(total: int, count: int) -> list[int]:
    if total <= 0 or count <= 0:
        return []
    if total <= count:
        return list(range(total))
    if count == 1:
        return [0]
    return sorted(
        {
            round(step * (total - 1) / (count - 1))
            for step in range(count)
        }
    )


def _join_selected_passages(
    passages: list[str],
    *,
    indices: list[int],
    max_chars: int,
) -> str:
    selected: list[str] = []
    used_chars = 0

    for index in sorted(dict.fromkeys(indices)):
        if index < 0 or index >= len(passages):
            continue

        passage = passages[index].strip()
        if not passage:
            continue

        addition = len(passage) + (2 if selected else 0)
        if selected and used_chars + addition > max_chars:
            continue

        if not selected and len(passage) > max_chars:
            return passage[:max_chars].strip()

        selected.append(passage)
        used_chars += addition

    if selected:
        return "\n\n".join(selected).strip()

    fallback = "\n\n".join(passages).strip()
    return fallback[:max_chars].strip()


def _select_passages_from_indices(
    passages: list[str],
    *,
    indices: list[int],
    max_chars: int,
) -> list[str]:
    selected: list[str] = []
    used_chars = 0

    for index in sorted(dict.fromkeys(indices)):
        if index < 0 or index >= len(passages):
            continue

        passage = passages[index].strip()
        if not passage:
            continue

        addition = len(passage) + (2 if selected else 0)
        if selected and used_chars + addition > max_chars:
            continue

        if not selected and len(passage) > max_chars:
            selected.append(passage[:max_chars].strip())
            break

        selected.append(passage)
        used_chars += addition

    if selected:
        return selected

    fallback = _join_selected_passages(passages, indices=list(range(len(passages))), max_chars=max_chars)
    return [fallback] if fallback else []


def _group_passages(
    passages: list[str],
    *,
    max_chars_per_group: int,
    max_groups: int,
) -> list[str]:
    if not passages:
        return []

    groups: list[str] = []
    current_parts: list[str] = []
    current_chars = 0

    for passage in passages:
        cleaned = passage.strip()
        if not cleaned:
            continue

        addition = len(cleaned) + (2 if current_parts else 0)
        if current_parts and current_chars + addition > max_chars_per_group:
            groups.append("\n\n".join(current_parts).strip())
            current_parts = [cleaned]
            current_chars = len(cleaned)
        elif not current_parts and len(cleaned) > max_chars_per_group:
            groups.append(cleaned[:max_chars_per_group].strip())
            current_parts = []
            current_chars = 0
        else:
            current_parts.append(cleaned)
            current_chars += addition

    if current_parts:
        groups.append("\n\n".join(current_parts).strip())

    if len(groups) <= max_groups:
        return groups

    selected_group_indices = _pick_evenly_spaced_indices(len(groups), max_groups)
    return [groups[index] for index in selected_group_indices]


def _serialize_outline_chunk_result(chunk_result: dict, *, chunk_index: int) -> str:
    modules = chunk_result.get("modules")
    lines = [f"Chunk {chunk_index}"]

    summary = str(chunk_result.get("summary") or "").strip()
    if summary:
        lines.append(f"Summary: {summary}")

    if isinstance(modules, list):
        for module in modules:
            if not isinstance(module, dict):
                continue
            title = str(module.get("title") or "").strip()
            description = str(module.get("description") or "").strip()
            keywords = module.get("keywords")
            keyword_text = ""
            if isinstance(keywords, list):
                keyword_text = ", ".join(
                    str(keyword).strip()
                    for keyword in keywords
                    if str(keyword).strip()
                )

            if title:
                lines.append(f"- Title: {title}")
            if description:
                lines.append(f"  Description: {description}")
            if keyword_text:
                lines.append(f"  Keywords: {keyword_text}")

    return "\n".join(lines).strip()


def _serialize_lesson_chunk_result(chunk_result: dict, *, chunk_index: int) -> str:
    lines = [f"Chunk {chunk_index}"]

    for field_name, label in (
        ("learning_objectives", "Learning objectives"),
        ("key_points", "Key points"),
        ("examples", "Examples"),
        ("warnings", "Warnings"),
        ("terms", "Terms"),
    ):
        values = chunk_result.get(field_name)
        if not isinstance(values, list):
            continue

        cleaned_values = [
            str(value).strip()
            for value in values
            if str(value).strip()
        ]
        if not cleaned_values:
            continue

        lines.append(f"{label}:")
        lines.extend(f"- {value}" for value in cleaned_values[:6])

    return "\n".join(lines).strip()


def _select_outline_passages(
    text: str,
    *,
    max_chars: int = OUTLINE_CONTEXT_CHARS,
) -> list[str]:
    passages = _split_passages(text)
    if not passages:
        return []

    full_text = "\n\n".join(passages)
    if len(full_text) <= max_chars:
        return passages

    target_count = min(len(passages), max(8, max_chars // 1600))
    indices = _pick_evenly_spaced_indices(len(passages), target_count)
    return _select_passages_from_indices(passages, indices=indices, max_chars=max_chars)


def _build_outline_context(text: str, *, max_chars: int = OUTLINE_CONTEXT_CHARS) -> str:
    passages = _select_outline_passages(text, max_chars=max_chars)
    return "\n\n".join(passages).strip()


def _build_module_context(
    text: str,
    *,
    module_title: str,
    module_description: str,
    max_chars: int = LESSON_CONTEXT_CHARS,
) -> str:
    passages = _select_module_passages(
        text,
        module_title=module_title,
        module_description=module_description,
        max_chars=max_chars,
    )
    return "\n\n".join(passages).strip()


def _select_module_passages(
    text: str,
    *,
    module_title: str,
    module_description: str,
    max_chars: int = LESSON_CONTEXT_CHARS,
) -> list[str]:
    passages = _split_passages(text)
    if not passages:
        return []

    full_text = "\n\n".join(passages)
    if len(full_text) <= max_chars:
        return passages

    keywords = _extract_keywords(module_title, module_description)
    scored_indices = sorted(
        range(len(passages)),
        key=lambda index: (_score_passage(passages[index], keywords), -index),
        reverse=True,
    )

    selected_indices: list[int] = []
    selected_set: set[int] = set()

    for base_index in range(min(2, len(passages))):
        selected_indices.append(base_index)
        selected_set.add(base_index)

    for index in scored_indices:
        if _score_passage(passages[index], keywords) <= 0:
            break

        for candidate in (index - 1, index, index + 1):
            if candidate < 0 or candidate >= len(passages) or candidate in selected_set:
                continue
            selected_indices.append(candidate)
            selected_set.add(candidate)
            if len(selected_indices) >= max(10, max_chars // 1200):
                break
        if len(selected_indices) >= max(10, max_chars // 1200):
            break

    if len(selected_indices) < 6:
        for index in _pick_evenly_spaced_indices(len(passages), 8):
            if index not in selected_set:
                selected_indices.append(index)
                selected_set.add(index)

    return _select_passages_from_indices(passages, indices=selected_indices, max_chars=max_chars)


def _build_learning_objectives(module_title: str, module_description: str) -> list[str]:
    objectives: list[str] = []
    for fragment in re.split(r"[\n\.;:]+", module_description or ""):
        cleaned = fragment.strip(" -\t")
        if cleaned:
            objectives.append(cleaned)
        if len(objectives) >= 4:
            break

    if not objectives:
        objectives.extend(
            [
                f"Nam duoc cac noi dung cot loi cua module {module_title}.",
                "Rut ra cac khai niem, quy trinh, luu y quan trong tu tai lieu goc.",
            ]
        )

    return objectives[:4]


def _extract_json_candidate(content: str) -> str:
    cleaned = _strip_code_fences(content)
    if not cleaned:
        return ""

    if cleaned.startswith("{") and cleaned.endswith("}"):
        return cleaned

    start_index = cleaned.find("{")
    end_index = cleaned.rfind("}")
    if start_index != -1 and end_index != -1 and end_index > start_index:
        return cleaned[start_index : end_index + 1].strip()

    return cleaned


def _parse_json_object(content: str) -> dict:
    candidate = _extract_json_candidate(content)
    if not candidate:
        raise AIResponseFormatError("AI returned empty content while JSON was expected")

    try:
        parsed = json.loads(candidate)
    except JSONDecodeError as exc:
        raise AIResponseFormatError(
            f"AI returned invalid JSON: {exc.msg} at line {exc.lineno} column {exc.colno}"
        ) from exc

    if not isinstance(parsed, dict):
        raise AIResponseFormatError("AI did not return a valid JSON object")

    return parsed


def _get_client() -> Groq:
    api_key = settings.GROQ_API_KEY
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")
    return Groq(api_key=api_key)


def call_llm(
    prompt: str,
    *,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    temperature: float = 0.2,
    max_completion_tokens: int | None = None,
) -> str:
    client = _get_client()
    request_kwargs = {
        "model": DEFAULT_MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": temperature,
    }
    if max_completion_tokens is not None:
        request_kwargs["max_completion_tokens"] = max_completion_tokens

    response = client.chat.completions.create(
        **request_kwargs,
    )
    return response.choices[0].message.content or "{}"


def _call_json(
    prompt: str,
    *,
    system_prompt: str,
    temperature: float = 0.2,
    max_attempts: int = 2,
    max_completion_tokens: int | None = None,
) -> dict:
    last_error: AIResponseFormatError | None = None

    for attempt in range(1, max_attempts + 1):
        retry_prompt = prompt
        retry_system_prompt = system_prompt

        if attempt > 1:
            retry_prompt = (
                f"{prompt}\n\n"
                "IMPORTANT: Return exactly one valid JSON object. "
                "Do not add markdown fences, commentary, or explanatory text."
            )
            retry_system_prompt = (
                f"{system_prompt} Return only JSON with no markdown fences or extra text."
            )

        content = call_llm(
            retry_prompt,
            system_prompt=retry_system_prompt,
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
        )

        try:
            return _parse_json_object(content)
        except AIResponseFormatError as exc:
            last_error = exc
            logger.warning(
                "AI JSON parsing failed. attempt=%s model=%s error=%s preview=%s",
                attempt,
                DEFAULT_MODEL_NAME,
                exc,
                _truncate_preview(content),
            )

    raise last_error or AIResponseFormatError("AI returned an invalid JSON response")


def _generate_outline_chunk_summary(chunk_text: str, *, chunk_index: int, total_chunks: int) -> dict:
    prompt = f"""
    Day la phan {chunk_index}/{total_chunks} cua bo tai lieu hoc.
    Hay rut ra cac chu de va module ung vien chi tu phan nay.
    Chi tra ve JSON hop le, ngan gon, khong giai thich them.
    Moi module nen cu the, tranh dat ten qua chung chung.

    Tai lieu:
    {chunk_text}

    JSON mau:
    {{
        "summary": "Tom tat ngan ve phan tai lieu nay",
        "modules": [
            {{
                "title": "Ten module",
                "description": "Dieu se hoc trong module nay",
                "keywords": ["tu khoa 1", "tu khoa 2"]
            }}
        ]
    }}
    """

    return _call_json(
        prompt,
        system_prompt=(
            "You analyze one chunk of learning material and return a compact JSON summary "
            "with candidate modules only."
        ),
        temperature=0.1,
        max_completion_tokens=OUTLINE_CHUNK_COMPLETION_TOKENS,
    )


def _generate_lesson_chunk_notes(
    chunk_text: str,
    *,
    curriculum_title: str,
    overview: str,
    module_title: str,
    module_description: str,
    chunk_index: int,
    total_chunks: int,
) -> dict:
    prompt = f"""
    Day la phan {chunk_index}/{total_chunks} cua tai lieu lien quan den module sau.
    Hay rut ra ghi chu hoc tap ngan gon, bam sat tai lieu.
    Chi tra ve JSON hop le, khong giai thich them.

    Curriculum Title: {curriculum_title}
    Overview: {overview}
    Module Title: {module_title}
    Module Description: {module_description}

    Tai lieu:
    {chunk_text}

    JSON mau:
    {{
        "learning_objectives": ["muc tieu 1", "muc tieu 2"],
        "key_points": ["y chinh 1", "y chinh 2"],
        "examples": ["vi du 1"],
        "warnings": ["luu y 1"],
        "terms": ["thuat ngu 1", "thuat ngu 2"]
    }}
    """

    return _call_json(
        prompt,
        system_prompt=(
            "You extract concise structured lesson notes from one chunk of source material. "
            "Return valid JSON only."
        ),
        temperature=0.1,
        max_completion_tokens=LESSON_CHUNK_COMPLETION_TOKENS,
    )


def generate_curriculum_outline(text: str) -> dict:
    text = clean_learning_material_text(text)
    outline = extract_curriculum_outline_from_toc(text)
    if outline:
        return outline
    return generate_curriculum_outline_fallback(text)


def generate_curriculum_outline_fallback(text: str) -> dict:
    text = clean_learning_material_text(text)
    heading_entries = _select_toc_modules(
        [
            parsed
            for line in text.splitlines()
            if (parsed := _parse_toc_entry(line)) and not parsed.get("has_page_tail")
        ]
    )
    if heading_entries:
        return {
            "title": _infer_curriculum_title(text),
            "overview": "Outline nay duoc tao tu cac heading co san trong tai lieu sau khi lam sach du lieu.",
            "modules": [
                {
                    "title": entry["title"],
                    "description": f"Heading {entry['number']}: {entry['title']}",
                }
                for entry in heading_entries
            ],
        }

    passages = _split_passages(text)
    if not passages:
        raise RuntimeError("No outline context available")

    description = _normalize_block("\n\n".join(passages[:3]))
    if len(description) > 360:
        description = f"{description[:357].rstrip()}..."

    return {
        "title": "Curriculum tu tai lieu hoc tap",
        "overview": (
            "Tai lieu khong co muc luc/heading ro rang, nen he thong tao mot module chung "
            "tu noi dung da duoc lam sach."
        ),
        "modules": [
            {
                "title": "Noi dung tai lieu",
                "description": description,
            }
        ],
    }


def generate_module_content(text: str) -> dict:
    return generate_curriculum_outline(text)


def _toc_number_from_description(module_description: str) -> str | None:
    match = re.search(r"muc\s+luc\s+([^:]+):", module_description or "", flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _find_matching_toc_entry(
    entries: list[dict],
    *,
    module_title: str,
    module_description: str,
) -> tuple[int, dict] | tuple[None, None]:
    target_number = _toc_number_from_description(module_description)
    target_number_key = _compact_key(target_number or "")
    target_title_key = _compact_key(module_title)

    for index, entry in enumerate(entries):
        if target_number_key and _compact_key(entry.get("number", "")) == target_number_key:
            return index, entry

    for index, entry in enumerate(entries):
        entry_title_key = _compact_key(entry.get("title", ""))
        if not entry_title_key or not target_title_key:
            continue
        if entry_title_key == target_title_key:
            return index, entry
        if entry_title_key in target_title_key or target_title_key in entry_title_key:
            return index, entry

    return None, None


def _line_matches_toc_entry(line: str, entry: dict) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 180:
        return False

    line_key = _compact_key(stripped)
    title_key = _compact_key(entry.get("title", ""))
    number_key = _compact_key(entry.get("number", ""))

    if title_key and (title_key in line_key or (len(line_key) >= 10 and line_key in title_key)):
        return True
    if number_key and line_key.startswith(number_key):
        title_tokens = [token for token in title_key.split() if len(token) >= 3]
        if not title_tokens or any(token in line_key for token in title_tokens[:4]):
            return True
    return False


def _alnum_count(text: str) -> int:
    return sum(char.isalnum() for char in text or "")


def _limit_source_text(text: str, *, max_chars: int) -> str:
    passages = _split_passages(text)
    if not passages:
        return ""
    return _join_selected_passages(
        passages,
        indices=list(range(len(passages))),
        max_chars=max_chars,
    )


def _extract_entry_section_text(
    lines: list[str],
    entries: list[dict],
    *,
    entry_index: int,
    toc_end_index: int,
) -> str:
    current_entry = entries[entry_index]
    start_line: int | None = None
    for index in range(max(toc_end_index, 0), len(lines)):
        if _line_matches_toc_entry(lines[index], current_entry):
            start_line = index
            break

    if start_line is None:
        return ""

    end_line = len(lines)
    for next_entry in entries[entry_index + 1 :]:
        if next_entry["level"] > current_entry["level"]:
            continue
        for candidate_index in range(start_line + 1, len(lines)):
            if _line_matches_toc_entry(lines[candidate_index], next_entry):
                end_line = candidate_index
                break
        if end_line != len(lines):
            break

    return "\n".join(lines[start_line:end_line]).strip()


def _find_parent_toc_index(entries: list[dict], entry_index: int) -> int | None:
    current_level = entries[entry_index]["level"]
    for parent_index in range(entry_index - 1, -1, -1):
        if entries[parent_index]["level"] < current_level:
            return parent_index
    return None


def _extract_source_section(
    cleaned_text: str,
    *,
    module_title: str,
    module_description: str,
    max_chars: int = LESSON_CONTEXT_CHARS,
) -> str:
    lines = cleaned_text.splitlines()
    entries, toc_end_index = _find_toc_entries(cleaned_text)
    entry_index, current_entry = _find_matching_toc_entry(
        entries,
        module_title=module_title,
        module_description=module_description,
    )

    if current_entry:
        section = _extract_entry_section_text(
            lines,
            entries,
            entry_index=entry_index or 0,
            toc_end_index=toc_end_index,
        )
        if section and _alnum_count(section) < 700:
            parent_index = _find_parent_toc_index(entries, entry_index or 0)
            if parent_index is not None:
                parent_section = _extract_entry_section_text(
                    lines,
                    entries,
                    entry_index=parent_index,
                    toc_end_index=toc_end_index,
                )
                if _alnum_count(parent_section) > _alnum_count(section):
                    section = parent_section
        limited_section = _limit_source_text(section, max_chars=max_chars)
        if limited_section:
            return limited_section

    body_text = "\n".join(lines[toc_end_index:]).strip() if toc_end_index else cleaned_text
    return _build_module_context(
        body_text,
        module_title=module_title,
        module_description=module_description,
        max_chars=max_chars,
    )


def build_module_source_description(
    *,
    text: str,
    module_title: str,
    module_description: str,
    max_chars: int = 700,
) -> str:
    cleaned_text = clean_learning_material_text(text)
    source_section = _extract_source_section(
        cleaned_text,
        module_title=module_title,
        module_description=module_description,
        max_chars=max_chars * 2,
    )
    passages = _split_passages(source_section)
    if not passages:
        return module_description.strip()

    summary = _join_selected_passages(
        passages,
        indices=list(range(min(len(passages), 4))),
        max_chars=max_chars,
    )
    return summary.strip()


def generate_lesson_content_from_source(
    *,
    text: str,
    curriculum_title: str,
    overview: str,
    module_title: str,
    module_description: str,
) -> str:
    cleaned_text = clean_learning_material_text(text)
    source_section = _extract_source_section(
        cleaned_text,
        module_title=module_title,
        module_description=module_description,
    )
    passages = _split_passages(source_section)
    if not passages:
        passages = [
            module_description.strip()
            or f"Tai lieu chua co noi dung ro rang cho module {module_title}."
        ]

    source_content = _join_selected_passages(
        passages,
        indices=list(range(len(passages))),
        max_chars=LESSON_CONTEXT_CHARS,
    )
    source_content = format_readable_paragraphs(
        source_content,
        max_sentences_per_paragraph=3,
    )
    overview_block = overview.strip() if overview and overview.strip() else "Tao tu muc luc va noi dung tai lieu goc."

    return f"""# {module_title}

## Boi canh
- Curriculum: {curriculum_title}
- Tong quan: {overview_block}

## Noi dung tu tai lieu
{source_content}

## Cau hoi on tap
- Cac y chinh trong phan "{module_title}" la gi?
- Phan nay co nhung khai niem, quy trinh, hoac luu y nao can ghi nho?
- Neu ap dung noi dung nay vao bai tap/thuc te, ban se bat dau tu dau?
""".strip()


def generate_lesson_content(
    *,
    text: str,
    curriculum_title: str,
    overview: str,
    module_title: str,
    module_description: str,
) -> str:
    return generate_lesson_content_from_source(
        text=text,
        curriculum_title=curriculum_title,
        overview=overview,
        module_title=module_title,
        module_description=module_description,
    )


def generate_lesson_content_fallback(
    *,
    text: str,
    curriculum_title: str,
    overview: str,
    module_title: str,
    module_description: str,
) -> str:
    try:
        return generate_lesson_content_from_source(
            text=text,
            curriculum_title=curriculum_title,
            overview=overview,
            module_title=module_title,
            module_description=module_description,
        )
    except Exception:
        cleaned_text = clean_learning_material_text(text)
        source_content = _limit_source_text(
            cleaned_text,
            max_chars=LESSON_CONTEXT_CHARS,
        )
        source_content = format_readable_paragraphs(
            source_content,
            max_sentences_per_paragraph=3,
        )
        if not source_content:
            source_content = (
                "Khong tim thay noi dung sach, co gia tri hoc tap cho bai hoc nay "
                "trong tai lieu da tai len."
            )

    overview_block = (
        overview.strip()
        if overview and overview.strip()
        else "Tao tu noi dung tai lieu goc sau khi lam sach du lieu."
    )

    return f"""# {module_title}

## Boi canh
- Curriculum: {curriculum_title}
- Tong quan: {overview_block}

## Noi dung tu tai lieu
{source_content}

## Cau hoi on tap
- Cac y chinh trong phan "{module_title}" la gi?
- Phan nay co nhung khai niem, quy trinh, hoac luu y nao can ghi nho?
- Neu ap dung noi dung nay vao bai tap/thuc te, ban se bat dau tu dau?
""".strip()


def call_lln(text: str) -> dict:
    return generate_curriculum_outline(text)


def generate_lession_content(
    *,
    text: str,
    curriculum_title: str,
    overview: str,
    module_title: str,
    module_description: str,
) -> str:
    return generate_lesson_content(
        text=text,
        curriculum_title=curriculum_title,
        overview=overview,
        module_title=module_title,
        module_description=module_description,
    )
def assign_passages_to_modules(passages: list[str], modules: list[dict]) -> list[list[str]]:
    """
    Gán mỗi passage cho module phù hợp nhất dựa vào từ khóa (title, description).
    Nếu không có điểm phù hợp, gán cho module đầu tiên.
    """
    module_keywords = [
        _extract_keywords(module.get("title", ""), module.get("description", ""))
        for module in modules
    ]
    module_passages = [[] for _ in modules]

    for passage in passages:
        scores = [
            _score_passage(passage, keywords)
            for keywords in module_keywords
        ]
        best_module_idx = scores.index(max(scores)) if max(scores) > 0 else 0
        module_passages[best_module_idx].append(passage)
    return module_passages

def split_text_by_modules(text: str, modules: list[dict]) -> list[str]:
    """
    Chia nội dung text thành các phần nhỏ tương ứng với từng module.
    """
    passages = _split_passages(text)
    module_passages = assign_passages_to_modules(passages, modules)
    return ["\n\n".join(pass_list) for pass_list in module_passages]

def assign_content_to_modules(text: str, modules: list[dict]) -> list[dict]:
    """
    Gán nội dung phù hợp cho từng module dựa vào text và mục lục modules.
    Trả về danh sách module có thêm trường 'content'.
    """
    module_contents = split_text_by_modules(text, modules)
    for i, module in enumerate(modules):
        module["content"] = module_contents[i]
    return modules
