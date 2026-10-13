# XML Character Reference Decoder

Decodes the numeric character references `&#1234;` and `&#x1F600;` as defined by XML 1.0 into their literal characters.

```python
from xml_character_reference_decoder import decode, decode_iter

assert decode("&#65;&#x42;") == "AB"

for is_decoded, chunk in decode_iter("A&#66;C"):
    print(is_decoded, chunk)
# False A
# True B
# False C
```

## Why this exists

XML text can carry characters as numeric references, and a surprising amount of real-world data mixes literal characters and references in the same field. When you just want the text out — for indexing, comparison, or display — you need a decoder that is tolerant of partial or malformed references rather than one that throws and aborts the whole document.

The deliberate trade-off: this library decodes only the two numeric forms. Named entities such as `&amp;` are left alone, because resolving them correctly requires the document's DTD, which we do not have. Trying to guess would produce wrong results on real documents; refusing is honest.

## Edge case you will hit

Malformed and out-of-range references are passed through verbatim rather than raising. A reference like `&#xD800;` (a lone surrogate) or `&#1;` (a control character disallowed by XML 1.0) is not decoded — the original text is preserved so no data is lost. If you need strict rejection, check the `(False, ...)` tuples from `decode_iter` and decide for yourself.

The `x` in `&#x...;` is lowercase by spec; `&#X61;` is not a reference and is left untouched.

## Exported names

- `decode(text: str) -> str` — decode all numeric character references, passing malformed ones through unchanged.
- `decode_iter(text: str)` — iterator yielding `(is_decoded: bool, chunk: str)` tuples, for callers that need to know which text came from a reference.

## Performance

The window keeps a bounded buffer, so `push` is constant time and memory does not
grow with the length of the stream. `peak` and `trough` are linear in the window
size, which is the trade that keeps `push` cheap.

