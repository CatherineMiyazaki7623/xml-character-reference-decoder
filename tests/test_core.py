import unittest

from xml_character_reference_decoder import decode, decode_iter


class TestDecimalReferences(unittest.TestCase):
    def test_simple_decimal(self):
        self.assertEqual(decode("&#65;"), "A")

    def test_decimal_among_text(self):
        self.assertEqual(decode("A&#66;C"), "ABC")

    def test_multiple_decimal(self):
        self.assertEqual(decode("&#72;&#105;"), "Hi")

    def test_newline_reference(self):
        self.assertEqual(decode("a&#10;b"), "a\nb")


class TestHexReferences(unittest.TestCase):
    def test_simple_hex_lowercase(self):
        self.assertEqual(decode("&#x61;"), "a")

    def test_simple_hex_uppercase(self):
        self.assertEqual(decode("&#x41;"), "A")

    def test_hex_mixed_case(self):
        self.assertEqual(decode("&#x1F600;"), chr(0x1F600))

    def test_hex_with_capital_X(self):
        # XML requires a lowercase 'x' after '#'; a capital 'X' is not a
        # reference at all and must pass through untouched.
        self.assertEqual(decode("&#X61;"), "&#X61;")


class TestMixedAndAdjacent(unittest.TestCase):
    def test_decimal_and_hex(self):
        self.assertEqual(decode("&#65;&#x42;"), "AB")

    def test_adjacent_references(self):
        self.assertEqual(decode("&#65;&#66;&#67;"), "ABC")

    def test_reference_at_start_and_end(self):
        self.assertEqual(decode("&#65;middle&#90;"), "A" + "middle" + "Z")


class TestEdgeCases(unittest.TestCase):
    def test_empty_string(self):
        self.assertEqual(decode(""), "")

    def test_no_references(self):
        self.assertEqual(decode("plain text"), "plain text")

    def test_amp_alone_not_a_reference(self):
        self.assertEqual(decode("AT&T"), "AT&T")

    def test_missing_semicolon(self):
        self.assertEqual(decode("&#65"), "&#65")

    def test_missing_digits(self):
        # An empty reference body is not a valid reference; leave it be.
        self.assertEqual(decode("&#; and &#x;"), "&#; and &#x;")

    def test_surrogate_codepoint_passes_through(self):
        # 0xD800 is a lone surrogate; chr() would build a surrogate
        # which is invalid in well-formed XML text. We pass the original
        # reference through instead.
        self.assertEqual(decode("&#xD800;"), "&#xD800;")

    def test_codepoint_above_max_passes_through(self):
        self.assertEqual(decode("&#x110000;"), "&#x110000;")

    def test_control_char_passes_through(self):
        # 0x01 is not in the XML 1.0 Char production; we keep the text.
        self.assertEqual(decode("&#1;"), "&#1;")

    def test_tab_and_cr_are_valid(self):
        # 0x09 (tab) and 0x0D (CR) are explicitly permitted by XML 1.0.
        self.assertEqual(decode("&#9;&#13;"), "\t\r")

    def test_decimal_zero(self):
        # 0x00 is not a valid XML character; we pass it through.
        self.assertEqual(decode("&#0;"), "&#0;")


class TestDecodeIter(unittest.TestCase):
    def test_iter_yields_tuples(self):
        chunks = list(decode_iter("A&#66;C"))
        self.assertEqual(chunks, [(False, "A"), (True, "B"), (False, "C")])

    def test_iter_only_text(self):
        self.assertEqual(list(decode_iter("hello")), [(False, "hello")])

    def test_iter_only_reference(self):
        self.assertEqual(list(decode_iter("&#65;")), [(True, "A")])

    def test_iter_malformed_passthrough(self):
        chunks = list(decode_iter("&#1;"))
        self.assertEqual(chunks, [(False, "&#1;")])

    def test_iter_empty(self):
        self.assertEqual(list(decode_iter("")), [])

    def test_iter_reconstructs_text(self):
        original = "&#72;ello&#x21;"
        rejoined = "".join(c for _, c in decode_iter(original))
        self.assertEqual(rejoined, decode(original))


if __name__ == "__main__":
    unittest.main()
