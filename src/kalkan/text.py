"""Normalization and intent checks shared by the screen, judge, and sandbox agent."""

from __future__ import annotations

import re
import unicodedata

# Latin letters that attackers swap for Cyrillic or Greek lookalikes.
_CONFUSABLES = str.maketrans(
    {
        "а": "a",
        "с": "c",
        "е": "e",
        "і": "i",
        "о": "o",
        "р": "p",
        "ѕ": "s",
        "у": "y",
        "х": "x",
        "ο": "o",
        "α": "a",
        "ε": "e",
    }
)

_ZERO_WIDTH = re.compile(r"[\u200b\u200c\u200d\ufeff]")
_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_NEGATION = re.compile(
    r"(don't|dont|\bnot\b|\bnever\b|\bwithout\b|değil|degil|gönderme|gonderme|\biletme\b|\byapma\b)"
)

FORWARD_REQUEST = re.compile(
    r"("
    r"\bforward(?:\s+(?:the|all|my))?\s+(?:files|documents|attachments)\b|"
    r"\bdosyalar[ıi]\s+(?:ilet|gönder|gonder|yolla|aktar)\b"
    r")"
)
SEND_REQUEST = re.compile(
    r"("
    r"\bsend\b.{0,40}\b(?:email|e-mail|reply|message|confirmation)\b|"
    r"\be-?postas[ıi]n[ıi]\s+(?:gönder|gonder|yolla)\b|"
    r"\badresine\s+(?:gönder|gonder|yolla)\b"
    r")"
)


def normalize(text: str) -> str:
    """Fold case, zero-width characters, and a few confusable letters.

    Turkish İ is mapped to I before case-folding so it does not become i plus
    a combining dot. Other Turkish letters (ö, ü, ş, ğ, ç, ı) are preserved.
    """
    folded = unicodedata.normalize("NFKC", text)
    folded = folded.replace("\u0130", "I")
    folded = _ZERO_WIDTH.sub("", folded)
    folded = folded.lower().replace("\u0307", "")
    folded = folded.translate(_CONFUSABLES)
    folded = re.sub(r"\s+", " ", folded).strip()
    return folded


def find_emails(text: str) -> list[str]:
    return _EMAIL.findall(text)


def phrase_authorized(intent: str, pattern: re.Pattern[str], recipient: str = "") -> bool:
    """True when a positive request survives a nearby negation and names the recipient."""
    folded = intent.lower()
    for match in pattern.finditer(folded):
        window = folded[max(0, match.start() - 40) : match.start()]
        if _NEGATION.search(window):
            continue
        if recipient and recipient.lower() not in folded:
            continue
        return True
    return False
