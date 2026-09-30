"""Decode XML character references into their literal characters.

This module handles the two numeric forms XML 1.0 defines:

    &#1234;   decimal character reference
    &#x1F600; hexadecimal character reference

Named entities (&amp;, &lt;, etc.) are intentionally NOT handled here. The
XML spec ties those to the DTD, which means a correct resolver needs the
document's DTD in hand. That is a different problem and belongs in a
different library; conflating the two is how half-broken entity
resolvers get written.

Design notes
------------
``decode`` builds the full string eagerly, which is the convenient shape
for most callers. ``decode_iter`` yields (text, chunk) tuples so a
caller can preserve the position of each reference (useful for
streaming parsers and error reporting) without re-scanning the string.

Characters are assembled via chr() once a code point is known. We do
NOT use a translation table or str.translate because the input may
contain malformed references that must be passed through verbatim; a
table-based approach cannot distinguish 'no reference here' from
'reference that failed to parse'.
"""

import re

# XML 1.0 reference production:
#   CharRef ::= '&#' [0-9]+ ';' | '&#x' [0-9a-fA-F]+ ';'
# We require at least one digit after the # or #x so that bare '&#' or
# '&#x;' are left untouched rather than crashing with an empty int().
_PATTERN = re.compile(
    r"&#x([0-9a-fA-F]+);|&#([0-9]+);",
)

# XML 1.0 valid character ranges, per the spec's Char production. We
# reject anything outside these because the spec does, and feeding
# chr() a surrogate or control char silently produces junk text.
#   Char ::= #x9 | #xA | #xD | #x20-#xD7FF | #xE000-#xFFFD
#           | #x10000-#x10FFFF
_VALID_RANGES = (
    (0x09, 0x09),
    (0x0A, 0x0A),
    (0x0D, 0x0D),
    (0x20, 0xD7FF),
    (0xE000, 0xFFFD),
    (0x10000, 0x10FFFF),
)


def _is_valid_xml_char(cp: int) -> bool:
    """Return True if cp is a permitted XML 1.0 character."""
    for lo, hi in _VALID_RANGES:
        if lo <= cp <= hi:
            return True
    return False


def _codepoint_to_char(cp: int) -> str:
    """Convert a code point to a single-character string.

    Raises ValueError for surrogate code points and for code points
    outside the XML 1.0 Char production. We treat these as decode
    failures so the caller can fall back to the original text — which
    is exactly what an XML processor is required to do for a
    well-formedness error.
    """
    if cp < 0:
        raise ValueError("negative code point")
    if 0xD800 <= cp <= 0xDFFF:
        raise ValueError("surrogate code point")
    if not _is_valid_xml_char(cp):
        raise ValueError("code point outside XML 1.0 Char range")
    return chr(cp)


def decode_iter(text: str):
    """Yield decoded chunks of *text* as (is_decoded, str) tuples.

    is_decoded is True for chunks that came from a successfully
    decoded character reference, and False for literal text that was
    passed through (including malformed references, which are emitted
    verbatim so no data is lost).

    Iterating lets a caller reconstruct the original byte positions
    of references for error reporting without re-parsing.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a str")

    pos = 0
    for m in _PATTERN.finditer(text):
        if m.start() > pos:
            yield (False, text[pos:m.start()])
        # group 1 is the hex form; group 2 is the decimal form
        hex_part = m.group(1)
        digits = hex_part if hex_part is not None else m.group(2)
        base = 16 if hex_part is not None else 10
        try:
            cp = int(digits, base)
            ch = _codepoint_to_char(cp)
            yield (True, ch)
        except ValueError:
            # Malformed or out-of-range reference: emit the original
            # text unchanged so no data is silently dropped.
            yield (False, m.group(0))
        pos = m.end()

    if pos < len(text):
        yield (False, text[pos:])


def decode(text: str) -> str:
    """Return *text* with all numeric XML character references decoded.

    Malformed references (unparseable digits, out-of-range code points,
    lone surrogates) are passed through verbatim rather than raising —
    a decode function that throws on bad input is useless for cleaning
    untrusted text, which is the one place you actually need it.
    """
    return "".join(chunk for _, chunk in decode_iter(text))
