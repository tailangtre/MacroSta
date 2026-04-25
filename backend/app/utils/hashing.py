"""
MacroScope — Content hashing for cross-source deduplication.

Same wire story (Reuters, AP) gets republished by 5+ aggregators with
different URLs. URL dedup misses this; a normalized-title hash catches it.
"""
import hashlib
import re
import unicodedata


_PUNCT_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)
_WS_RE = re.compile(r"\s+")


def normalize_title(title: str) -> str:
    """Lowercase, strip accents/punctuation, collapse whitespace."""
    if not title:
        return ""
    # NFKD splits accented chars into base + combining mark; ascii() drops the marks
    decomposed = unicodedata.normalize("NFKD", title)
    ascii_only = decomposed.encode("ascii", "ignore").decode("ascii")
    no_punct = _PUNCT_RE.sub(" ", ascii_only.lower())
    return _WS_RE.sub(" ", no_punct).strip()


def content_hash(title: str, description: str = "") -> str:
    """SHA-1 hex digest of the normalized title plus first 100 chars of description.

    Description is included so two unrelated articles that happen to share
    a generic title ("Market Update") don't collide. 100 chars is enough
    for differentiation without making the hash sensitive to minor body edits.
    """
    norm_title = normalize_title(title)
    norm_desc = normalize_title(description or "")[:100]
    payload = f"{norm_title}|{norm_desc}".encode("utf-8")
    return hashlib.sha1(payload).hexdigest()
