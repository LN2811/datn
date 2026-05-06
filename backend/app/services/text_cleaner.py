import re
import unicodedata


VIETNAMESE_VOWELS = (
    "aăâeêioôơuưy"
    "AĂÂEÊIOÔƠUƯY"
    "áàảãạắằẳẵặấầẩẫậ"
    "éèẻẽẹếềểễệ"
    "íìỉĩị"
    "óòỏõọốồổỗộớờởỡợ"
    "úùủũụứừửữự"
    "ýỳỷỹỵ"
    "ÁÀẢÃẠẮẰẲẴẶẤẦẨẪẬ"
    "ÉÈẺẼẸẾỀỂỄỆ"
    "ÍÌỈĨỊ"
    "ÓÒỎÕỌỐỒỔỖỘỚỜỞỠỢ"
    "ÚÙỦŨỤỨỪỬỮỰ"
    "ÝỲỶỸỴ"
)
VIETNAMESE_CONSONANTS = "bcdfghjklmnpqrstvwxyzđBCDFGHJKLMNPQRSTVWXYZĐ"
VIETNAMESE_WORD_CHARS = "A-Za-zÀ-ỹĐđ"
VIETNAMESE_INITIAL_CLUSTERS = (
    "ngh",
    "ng",
    "nh",
    "ch",
    "gh",
    "gi",
    "kh",
    "ph",
    "qu",
    "th",
    "tr",
)
VIETNAMESE_INITIALS = (
    *VIETNAMESE_INITIAL_CLUSTERS,
    "b",
    "c",
    "d",
    "đ",
    "g",
    "h",
    "k",
    "l",
    "m",
    "n",
    "p",
    "r",
    "s",
    "t",
    "v",
    "x",
)

TONE_MARKS = {"\u0300", "\u0301", "\u0303", "\u0309", "\u0323"}
FOLDED_VOWELS = set("aeiouy")
SPLIT_FRAGMENT_RE = re.compile(
    rf"\b([{VIETNAMESE_WORD_CHARS}]{{1,5}})[ \t]+"
    rf"([{VIETNAMESE_VOWELS}][{VIETNAMESE_WORD_CHARS}]{{0,5}})\b",
    flags=re.UNICODE,
)

FOLDED_NUCLEUS_FINALS: dict[str, tuple[str, ...]] = {
    "a": ("", "c", "ch", "m", "n", "ng", "nh", "p", "t"),
    "e": ("", "c", "m", "n", "ng", "p", "t"),
    "i": ("", "ch", "m", "n", "nh", "p", "t"),
    "o": ("", "c", "ch", "m", "n", "ng", "p", "t"),
    "u": ("", "c", "m", "n", "ng", "p", "t"),
    "y": ("", "n", "t"),
    "ie": ("", "c", "m", "n", "ng", "p", "t"),
    "ye": ("", "c", "m", "n", "ng", "p", "t"),
    "ua": ("", "c", "n", "ng", "t"),
    "uo": ("", "c", "n", "ng", "t"),
    "oa": ("", "c", "ch", "n", "ng", "t"),
    "oe": ("", "n", "t"),
    "ue": ("", "n", "t"),
    "uy": ("", "ch", "n", "nh", "t"),
    "uye": ("", "n", "t"),
}
FOLDED_NO_FINAL_NUCLEI = {
    "ai",
    "ao",
    "au",
    "ay",
    "eo",
    "eu",
    "ia",
    "iu",
    "oi",
    "ui",
    "uu",
    "oai",
    "oay",
    "uay",
    "uoi",
    "uou",
    "ieu",
    "yeu",
}


def _fold_vietnamese(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value or "")
    return "".join(
        char
        for char in normalized
        if unicodedata.category(char) != "Mn"
    ).lower()


def _iter_combining_marks(value: str):
    for char in unicodedata.normalize("NFD", value or ""):
        if unicodedata.category(char) == "Mn":
            yield char


def has_vietnamese_mark(text: str) -> bool:
    return "đ" in (text or "").lower() or any(_iter_combining_marks(text))


def _has_vietnamese_tone(text: str) -> bool:
    return any(mark in TONE_MARKS for mark in _iter_combining_marks(text))


def _is_vietnamese_vowel(char: str) -> bool:
    return char in VIETNAMESE_VOWELS


def _contains_folded_vowel(value: str) -> bool:
    return any(char in FOLDED_VOWELS for char in _fold_vietnamese(value))


def _split_initial_and_rhyme(folded_syllable: str) -> tuple[str, str]:
    for initial in sorted(VIETNAMESE_INITIALS, key=len, reverse=True):
        if folded_syllable.startswith(initial):
            return initial, folded_syllable[len(initial):]
    return "", folded_syllable


def _is_valid_folded_rhyme(rhyme: str) -> bool:
    if not rhyme:
        return False
    if rhyme in FOLDED_NO_FINAL_NUCLEI:
        return True
    return any(
        rhyme == f"{nucleus}{final}"
        for nucleus, finals in FOLDED_NUCLEUS_FINALS.items()
        for final in finals
    )


def _is_plausible_vietnamese_syllable(value: str) -> bool:
    folded = _fold_vietnamese(value)
    if not re.fullmatch(r"[a-zđ]{2,8}", folded):
        return False
    _, rhyme = _split_initial_and_rhyme(folded)
    if not any(char in FOLDED_VOWELS for char in rhyme):
        return False
    return _is_valid_folded_rhyme(rhyme)


def _is_initial_fragment(left: str) -> bool:
    folded = _fold_vietnamese(left)
    return (
        len(folded) == 1
        and left in VIETNAMESE_CONSONANTS
        or folded in VIETNAMESE_INITIAL_CLUSTERS
    )


def _is_likely_split_vowel_sequence(left: str, right: str) -> bool:
    left_folded = _fold_vietnamese(left)
    right_folded = _fold_vietnamese(right)
    if not left_folded or not right_folded:
        return False
    if left_folded.endswith(("i", "y")):
        return right_folded.startswith("e")
    if left_folded.endswith("u"):
        return right_folded.startswith(("a", "e", "o", "y"))
    if left_folded.endswith("o"):
        return right_folded.startswith("a")
    return False


def should_join_vietnamese_fragment(left: str, right: str) -> bool:
    if not left or not right or len(left) > 5 or len(right) > 6:
        return False
    if not re.fullmatch(rf"[{VIETNAMESE_WORD_CHARS}]+", left + right):
        return False
    if not _is_vietnamese_vowel(right[0]):
        return False
    if has_vietnamese_mark(left) and _fold_vietnamese(left) != "đ":
        return False
    if not has_vietnamese_mark(right):
        return False

    combined = f"{left}{right}"
    if not _is_plausible_vietnamese_syllable(combined):
        return False

    if _is_initial_fragment(left):
        return True
    if not _contains_folded_vowel(left):
        return True
    if _has_vietnamese_tone(right):
        return _is_likely_split_vowel_sequence(left, right)

    right_first = right[0]
    if _fold_vietnamese(right_first) == "e" and left.lower().endswith(("i", "y")):
        return True
    if _fold_vietnamese(right_first) in {"o"} and left.lower().endswith("u"):
        return True
    return False


def clean_vietnamese_text(text: str) -> str:
    if not text:
        return ""

    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x0c", "\n")
    text = re.sub(r"[ \t]+", " ", text)

    def _join_fragment(match: re.Match[str]) -> str:
        left, right = match.group(1), match.group(2)
        line_start = text.rfind("\n", 0, match.start())
        line_prefix = text[line_start + 1 : match.start()].strip()
        if (
            len(left) == 1
            and left in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            and line_prefix
            and not line_prefix.endswith((".", ":", ";", "!", "?", "(", "[", "{", "-"))
        ):
            return match.group(0)
        if should_join_vietnamese_fragment(left, right):
            return f"{left}{right}"
        return match.group(0)

    for _ in range(2):
        text = SPLIT_FRAGMENT_RE.sub(_join_fragment, text)

    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\s+([,.!?;:%])", r"\1", text)
    text = re.sub(r"([([{])\s+", r"\1", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return unicodedata.normalize("NFC", text).strip()
