"""German G2P: text normalization + gruut phonemization.

normalize_text_de() expands numbers, dates, times, currency, and
abbreviations so gruut receives clean spelled-out text.

DEG2P wraps normalize_text_de() + GruutG2P for use in KPipeline.
"""

from typing import Optional, Tuple
import importlib.resources
import json
import re
import unicodedata
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from . import data

# ── cardinal numbers ─────────────────────────────────────────────────────────

_ONES = [
    "",
    "ein",
    "zwei",
    "drei",
    "vier",
    "fünf",
    "sechs",
    "sieben",
    "acht",
    "neun",
    "zehn",
    "elf",
    "zwölf",
    "dreizehn",
    "vierzehn",
    "fünfzehn",
    "sechzehn",
    "siebzehn",
    "achtzehn",
    "neunzehn",
]
_TENS = [
    "",
    "",
    "zwanzig",
    "dreißig",
    "vierzig",
    "fünfzig",
    "sechzig",
    "siebzig",
    "achtzig",
    "neunzig",
]
_LARGE_SCALES = [
    (1_000_000_000_000_000, "eine Trillion", "Trillionen"),
    (1_000_000_000_000, "eine Billion", "Billionen"),
    (1_000_000_000, "eine Milliarde", "Milliarden"),
    (1_000_000, "eine Million", "Millionen"),
]
_PHONE_NUMBER_RE = re.compile(r"(?<![\d.:])\d{2,4}(?:[ -]\d{2,6}){1,}(?![\d.:])")


def _int_to_de(n, standalone=True):
    """Convert integer to German words.

    standalone=True returns "eins" for 1, standalone=False returns "ein"
    (used in composition: einhundert, eintausend).
    """
    if n < 0:
        return "minus " + _int_to_de(-n)
    if n == 0:
        return "null"
    if n == 1:
        return "eins" if standalone else "ein"
    if n < 20:
        return _ONES[n]
    if n < 100:
        ones, tens = n % 10, n // 10
        if ones:
            return _ONES[ones] + "und" + _TENS[tens]
        return _TENS[tens]
    if n < 1_000:
        h, r = n // 100, n % 100
        return _ONES[h] + "hundert" + (_int_to_de(r, standalone=False) if r else "")
    if n < 1_000_000:
        t, r = n // 1_000, n % 1_000
        prefix = _int_to_de(t, standalone=False) if t != 1 else "ein"
        return prefix + "tausend" + (_int_to_de(r, standalone=False) if r else "")

    for divisor, singular, plural in _LARGE_SCALES:
        if n >= divisor:
            scale_count, r = divmod(n, divisor)
            word = singular if scale_count == 1 else _int_to_de(scale_count, standalone=False) + " " + plural
            return word + (" " + _int_to_de(r, standalone=False) if r else "")

    return _int_to_de(n)


# ── ordinals ─────────────────────────────────────────────────────────────────

_ORD_IRREG = {1: "erst", 2: "zweit", 3: "dritt", 7: "siebt", 8: "acht"}


def _ordinal_stem_de(n):
    """Ordinal stem without inflection suffix."""
    if n in _ORD_IRREG:
        return _ORD_IRREG[n]
    stem = _int_to_de(n, standalone=False) + ("t" if n < 20 else "st")
    if n == 100 or n == 1000:
        stem = stem.replace("ein", "", 1)
    return stem


def _ordinal_with_suffix_de(n, suffix):
    return _ordinal_stem_de(n) + suffix


# ── years ────────────────────────────────────────────────────────────────────


def _year_de(n):
    """German year pronunciation: 1985 -> neunzehnhundertfünfundachtzig."""
    if 1100 <= n <= 1999:
        c, r = n // 100, n % 100
        return (
            _int_to_de(c, standalone=False)
            + "hundert"
            + (_int_to_de(r, standalone=False) if r else "")
        )
    return _int_to_de(n)


# ── month names ──────────────────────────────────────────────────────────────

_MONTHS = [
    "",
    "Januar",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
]

# ── currency ─────────────────────────────────────────────────────────────────

_CURRENCY = {"€": "Euro", "$": "Dollar", "£": "Pfund", "¥": "Yen"}


def _currency_repl(sym, num):
    word = _CURRENCY.get(sym, sym)
    cleaned = num.replace(".", "").replace(",", ".")
    try:
        val = Decimal(cleaned)
    except InvalidOperation:
        return sym + num
    cents_total = int((val * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    euros, cents = divmod(cents_total, 100)
    if cents == 0:
        return _int_to_de(euros, standalone=False) + " " + word
    return _int_to_de(euros, standalone=False) + " " + word + " und " + _int_to_de(cents, standalone=False) + " Cent"


def _render_full_date(day, month, year, suffix):
    if day < 1 or day > 31 or month < 1 or month > 12:
        return None
    return _ordinal_with_suffix_de(day, suffix) + " " + _MONTHS[month] + " " + _year_de(year)


def _digits_to_de(digits):
    return " ".join(_int_to_de(int(d)) for d in digits)


def _phone_repl(match):
    groups = re.findall(r"\d+", match.group(0))
    return " ".join(_digits_to_de(group) for group in groups)


# ── text normalization ───────────────────────────────────────────────────────


def normalize_text_de(text):
    """Normalize German text for TTS: expand numbers, dates, times, currency, abbreviations."""
    if not text:
        return text

    # 1. Quotes -> ASCII
    text = text.replace("\u201e", '"').replace("\u201c", '"')  # „ "
    text = text.replace("\u2018", "'").replace("\u2019", "'")  # ' '
    text = text.replace("\u00ab", '"').replace("\u00bb", '"')  # « »
    text = text.replace("\u2039", '"').replace("\u203a", '"')  # ‹ ›

    # 2. Non-breaking whitespace
    text = re.sub(r"[^\S \n]", " ", text)

    # 3. Abbreviations
    text = re.sub(r"\bDr\.(?=\s)", "Doktor", text)
    text = re.sub(r"\bProf\.(?=\s)", "Professor", text)
    text = re.sub(r"\bHr\.(?=\s)", "Herr ", text)
    text = re.sub(r"\bFr\.(?=\s[A-ZÄÖÜ])", "Frau", text)
    text = re.sub(r"\bDipl\.\s*-?\s*Ing\.", "Diplom-Ingenieur", text)
    text = re.sub(r"\bStr\.(?=\s)", "Straße", text)
    text = re.sub(r"\bNr\.(?=\s*\d)", "Nummer", text)
    text = re.sub(r"\bTel\.(?=\s)", "Telefon", text)
    text = re.sub(r"\bAbt\.(?=\s)", "Abteilung", text)
    text = re.sub(r"\bgem\.(?=\s)", "gemäß", text, flags=re.IGNORECASE)
    text = re.sub(r"\bAbs\.(?=\s*\d)", "Absatz", text)
    text = re.sub(r"\bGmbH\b", "Gesellschaft mit beschränkter Haftung", text)
    text = re.sub(r"\bAG\b(?=[\s,.]|$)", "Aktiengesellschaft", text)
    text = re.sub(r"\bz\.\s*B\.", "zum Beispiel", text, flags=re.IGNORECASE)
    text = re.sub(r"\bd\.\s*h\.", "das heißt", text, flags=re.IGNORECASE)
    text = re.sub(r"\bu\.\s*a\.", "unter anderem", text, flags=re.IGNORECASE)
    text = re.sub(r"\bbzw\.", "beziehungsweise", text, flags=re.IGNORECASE)
    text = re.sub(r"\busw\.", "und so weiter", text, flags=re.IGNORECASE)
    text = re.sub(r"\betc\.", "et cetera", text, flags=re.IGNORECASE)
    text = re.sub(r"\bca\.", "circa", text, flags=re.IGNORECASE)
    text = re.sub(r"\bvgl\.", "vergleiche", text, flags=re.IGNORECASE)
    text = re.sub(r"\binkl\.", "inklusive", text, flags=re.IGNORECASE)
    text = re.sub(r"\bexkl\.", "exklusive", text, flags=re.IGNORECASE)
    text = re.sub(r"\bggf\.", "gegebenenfalls", text, flags=re.IGNORECASE)
    text = re.sub(r"\bi\.\s*d\.\s*R\.", "in der Regel", text, flags=re.IGNORECASE)
    text = re.sub(r"\bo\.\s*ä\.", "oder ähnliches", text, flags=re.IGNORECASE)
    text = re.sub(r"\bu\.\s*U\.", "unter Umständen", text, flags=re.IGNORECASE)
    # Month abbreviations
    for abbr, full in [
        ("Jan", "Januar"),
        ("Feb", "Februar"),
        ("Mär", "März"),
        ("Apr", "April"),
        ("Jun", "Juni"),
        ("Jul", "Juli"),
        ("Aug", "August"),
        ("Sep", "September"),
        ("Okt", "Oktober"),
        ("Nov", "November"),
        ("Dez", "Dezember"),
    ]:
        text = re.sub(rf"\b{abbr}\.(?=\s)", full, text)
    text = re.sub(r"§§\s*(?=\d)", "Paragrafen ", text)
    text = re.sub(r"§\s*(?=\d)", "Paragraf ", text)

    # 4. Currency (symbol before or after amount)
    csym = r"[€$£¥]"
    text = re.sub(
        rf"({csym})\s*(\d[\d.,]*)",
        lambda m: _currency_repl(m.group(1), m.group(2)),
        text,
    )
    text = re.sub(
        rf"(\d[\d.,]*)\s*({csym})",
        lambda m: _currency_repl(m.group(2), m.group(1)),
        text,
    )

    # 5. Times (HH:MM)
    def _time_repl(m):
        h, mi = int(m.group(1)), int(m.group(2))
        if h > 23 or mi > 59:
            return m.group(0)
        return _int_to_de(h) + " Uhr" + (" " + _int_to_de(mi) if mi else "")

    text = re.sub(r"\b(\d{1,2}):(\d{2})\b(?:\s*Uhr\b)?", _time_repl, text)

    # 6. Full dates (DD.MM.YYYY) with simple case-aware ordinal inflection.
    def _date_with_prefix_repl(m):
        prefix = m.group(1)
        day, month, year = int(m.group(2)), int(m.group(3)), int(m.group(4))
        suffix = 'en' if prefix.casefold() in {'am', 'im', 'vom', 'zum', 'den'} else 'e'
        rendered = _render_full_date(day, month, year, suffix)
        if rendered is None:
            return m.group(0)
        return prefix + ' ' + rendered

    def _date_repl(m):
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        rendered = _render_full_date(day, month, year, 'er')
        if rendered is None:
            return m.group(0)
        return rendered

    text = re.sub(r"\b(vom|am|im|zum|den|der)\s+(\d{1,2})\.(\d{1,2})\.(\d{4})\b", _date_with_prefix_repl, text, flags=re.IGNORECASE)
    text = re.sub(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b", _date_repl, text)

    # 7. Ordinals in common article contexts and general mid-sentence ordinals.
    text = re.sub(
        r"\b([Aa]m)\s+(\d+)\.\s",
        lambda m: m.group(1) + " " + _ordinal_stem_de(int(m.group(2))) + "en ",
        text,
    )
    text = re.sub(
        r"(?<!\d)(\d+)\.\s",
        lambda m: _ordinal_stem_de(int(m.group(1))) + "e ",
        text,
    )

    # 8. Standalone years (1100-2099)
    def _year_repl(m):
        n = int(m.group(1))
        return _year_de(n) if 1100 <= n <= 2099 else _int_to_de(n)

    text = re.sub(r"\b(\d{4})\b", _year_repl, text)

    # 9. German-format numbers: 1.234.567 or 1.234,56
    def _grouped_num_repl(m):
        cleaned = m.group(0).replace(".", "").replace(",", ".")
        try:
            val = float(cleaned)
        except ValueError:
            return m.group(0)
        if val == int(val):
            return _int_to_de(int(val))
        ip, fp = cleaned.split(".")
        return (
            _int_to_de(int(ip)) + " Komma " + " ".join(_int_to_de(int(d)) for d in fp)
        )

    text = re.sub(r"\b\d{1,3}(?:\.\d{3})+(?:,\d+)?\b", _grouped_num_repl, text)

    # Decimal comma (3,14)
    def _decimal_repl(m):
        ip, fp = m.group(1), m.group(2)
        return (
            _int_to_de(int(ip)) + " Komma " + " ".join(_int_to_de(int(d)) for d in fp)
        )

    text = re.sub(r"\b(\d+),(\d+)\b", _decimal_repl, text)

    # Phone-like digit groups should be read digit-by-digit instead of as one integer.
    text = _PHONE_NUMBER_RE.sub(_phone_repl, text)
    text = re.sub(r"\s*%", " Prozent", text)

    # Plain integers. Keep any invalid HH:MM text that survived the time pass unchanged.
    remaining_time_re = re.compile(r"\b\d{1,2}:\d{2}\b(?:\s*Uhr\b)?")

    def _plain_int_repl(m):
        start = max(0, m.start() - 3)
        end = min(len(text), m.end() + len(":00 Uhr"))
        for time_match in remaining_time_re.finditer(text, start, end):
            if time_match.start() <= m.start() and m.end() <= time_match.end():
                return m.group(0)
        return _int_to_de(int(m.group(1)))

    text = re.sub(r"\b(\d+)\b", _plain_int_repl, text)

    # 10. Whitespace cleanup
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    return text


# ── pronunciation overrides ──────────────────────────────────────────────────
#
# A small lexicon layer on top of espeak-de. espeak mispronounces English /
# brand / tech terms (GitHub, PyTorch, CUDA, ...) and a few foreign-origin
# German words. These overrides supply hand-written phonemes that bypass espeak
# and go straight to the model. Phonemes use the same symbol convention gruut's
# output is mapped to (see misaki_gruut.gruut.PAIRS), e.g. capital A/I/W/O/Y
# for diphthongs.
#
# Lookup keys are matched after normalize_for_lookup(): casefold, NFKD, strip
# combining marks, and fold "+"->"plus", "&"->"and", "@"->"at". This lets
# "Disney+" match "disneyplus" without any multi-word logic.


_LOOKUP_REPLACEMENTS = {"+": "plus", "&": "and", "@": "at"}

# Punctuation that attaches tightly to the preceding phoneme fragment.
_TRAILING_PUNCT = frozenset(".,!?;:%)]}»”")

# Word-ish tokens for override matching. Captures internal "-"/"'" (espeak-ng,
# zero-shot) and a trailing "+" (Disney+) so single tokens with joiners match
# their normalized override key. Space-separated multi-word brands are not
# matched here by design.
_OVERRIDE_WORD_RE = re.compile(
    r"[0-9A-Za-zÀ-ÖØ-öø-ÿß]+(?:['\-][0-9A-Za-zÀ-ÖØ-öø-ÿß]+)*\+?"
)


def normalize_for_lookup(text: str) -> str:
    """Collapse a word to its override-lookup key.

    Casefolds, applies NFKD and drops combining marks (so "Moët" -> "moet"),
    folds a few joiner symbols to words ("+" -> "plus"), and keeps only
    alphanumerics. Spaces and other punctuation are dropped, so "Prime Video"
    collapses to "primevideo".
    """
    text = unicodedata.normalize("NFKD", text.casefold())
    parts = []
    for char in text:
        if unicodedata.category(char) == "Mn":
            continue
        replacement = _LOOKUP_REPLACEMENTS.get(char)
        if replacement is not None:
            parts.append(replacement)
            continue
        if char.isalnum():
            parts.append(char)
    return "".join(parts)


def _load_overrides():
    """Load de_overrides.json and build the normalized lookup table.

    Priority on key collisions: brand > en > de_foreign (first writer wins).
    Returns (lookup, aliases) where lookup maps normalized keys to phonemes and
    aliases maps one normalized key to another.
    """
    with importlib.resources.open_text(data, "de_overrides.json") as r:
        raw = json.load(r)
    lookup = {}
    for section in ("brand", "en", "de_foreign"):
        for key, value in raw.get(section, {}).items():
            lookup.setdefault(normalize_for_lookup(key), value)
    aliases = {
        normalize_for_lookup(k): normalize_for_lookup(v)
        for k, v in raw.get("aliases", {}).items()
    }
    return lookup, aliases


_OVERRIDES, _OVERRIDE_ALIASES = _load_overrides()
_MAX_OVERRIDE_TOKENS = 4


def _resolve_override(text: str) -> Optional[str]:
    key = normalize_for_lookup(text)
    if not key:
        return None
    key = _OVERRIDE_ALIASES.get(key, key)
    return _OVERRIDES.get(key)


def override_for(word: str) -> Optional[str]:
    """Return override phonemes for a single word, or None if not overridden."""
    return _resolve_override(word)


def _find_phrase_override(text: str, matches, start_index: int):
    max_end = min(len(matches), start_index + _MAX_OVERRIDE_TOKENS)
    for end_index in range(max_end, start_index, -1):
        start = matches[start_index].start()
        end = matches[end_index - 1].end()
        phonemes = _resolve_override(text[start:end])
        if phonemes is not None:
            return end_index - 1, phonemes
    return None, None


# ── G2P class ────────────────────────────────────────────────────────────────


class DEG2P:
    """German G2P: normalize text then phonemize via gruut."""

    def __init__(self):
        from .gruut import GruutG2P

        self.phonemizer = GruutG2P(language="de-de")

    def _phonemes(self, text) -> str:
        if not text or not text.strip():
            return ""
        ps, _ = self.phonemizer(text)
        return ps or ""

    @staticmethod
    def _render(parts) -> str:
        # Join phoneme fragments with single spaces, but attach leading
        # punctuation (e.g. a fragment that is just "!") tightly to the
        # previous fragment, matching plain-espeak spacing.
        rendered = ""
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if not rendered:
                rendered = part
            elif part[0] in _TRAILING_PUNCT:
                rendered += part
            else:
                rendered += " " + part
        return rendered

    def __call__(self, text) -> Tuple[str, None]:
        text = normalize_text_de(text)

        # Find override words; everything between them is phonemized by gruut.
        # When no overrides match, this is identical to phonemizer(text).
        parts = []
        cursor = 0
        matches = list(_OVERRIDE_WORD_RE.finditer(text))
        i = 0
        while i < len(matches):
            match = matches[i]
            end_index, phonemes = _find_phrase_override(text, matches, i)
            if phonemes is None:
                i += 1
                continue
            preceding = text[cursor:match.start()]
            if preceding.strip():
                parts.append(self._phonemes(preceding))
            parts.append(phonemes)
            cursor = matches[end_index].end()
            i = end_index + 1

        if cursor == 0:
            return self.phonemizer(text)

        trailing = text[cursor:]
        if trailing.strip():
            parts.append(self._phonemes(trailing))

        return self._render(parts), None
