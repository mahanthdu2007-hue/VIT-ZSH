"""§12 numeric guardrail: every number in LLM text must appear in ENGINE_RESULT or CONTEXT.

Indian formats are normalized before comparing: 5,00,000 / 500000 / 5 lakh / 5L / ₹5L / 5 LPA all mean 500000.
A number written with fewer decimals than the source counts as the same value (26.43 may be written 26.4), and a
fraction may be written as a percentage (0.85 as 85%).
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

_NUM = r"\d+(?:,\d+)*(?:\.\d+)?"
_CURRENCY = r"(?:₹|rs\.?|inr)"
_UNIT = r"lakhs?|lacs?|lpa|crores?|cr|l|k|thousand|%"
_TOKEN = re.compile(
    rf"(?<![\w.]){_CURRENCY}?\s*(?P<a>{_NUM})"
    rf"(?:\s*(?:-|–|—|to)\s*{_CURRENCY}?\s*(?P<b>{_NUM}))?"
    rf"(?:\s*(?P<unit>{_UNIT})(?![a-z]))?",
    re.IGNORECASE,
)
_MULTIPLIERS = {"lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "lacs": 1e5, "lpa": 1e5, "l": 1e5,
                "crore": 1e7, "crores": 1e7, "cr": 1e7, "k": 1e3, "thousand": 1e3}
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z₹\"'(])")


@dataclass(frozen=True)
class NumberToken:
    text: str
    value: float  # as written, before the unit
    multiplier: float
    decimals: int


def extract_numbers(text: str) -> list[NumberToken]:
    """Every number in `text` with its unit; a range like ₹2–5 lakh applies the unit to both ends."""
    tokens: list[NumberToken] = []
    for match in _TOKEN.finditer(text):
        unit = (match.group("unit") or "").lower()
        multiplier = _MULTIPLIERS.get(unit, 1.0)
        for part in (match.group("a"), match.group("b")):
            if part is None:
                continue
            plain = part.replace(",", "")
            decimals = len(plain.split(".")[1]) if "." in plain else 0
            tokens.append(NumberToken(match.group(0).strip(), float(plain), multiplier, decimals))
    return tokens


def _walk(value: Any) -> Iterable[float | str]:
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        yield float(value)
    elif isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _walk(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk(item)


def allowed_values(*sources: Any) -> set[float]:
    """All values the LLM may quote: numbers in the JSON sources (fractions also as percentages) and every number
    written inside their strings, both as written and with its unit applied."""
    allowed: set[float] = set()
    for source in sources:
        for item in _walk(source):
            if isinstance(item, float):
                allowed.add(item)
                if 0 <= item <= 1:
                    allowed.add(item * 100)
            else:
                for token in extract_numbers(item):
                    allowed.update({token.value, token.value * token.multiplier})
    return allowed


def _rounded(value: float, decimals: int) -> Decimal:
    return Decimal(str(value)).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)


def is_supported(token: NumberToken, allowed: set[float]) -> bool:
    written = _rounded(token.value, token.decimals)
    return any(_rounded(v / token.multiplier, token.decimals) == written for v in allowed)


def unsupported_numbers(text: str, allowed: set[float]) -> list[str]:
    return [t.text for t in extract_numbers(text) if not is_supported(t, allowed)]


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_END.split(text.strip()) if s.strip()]
