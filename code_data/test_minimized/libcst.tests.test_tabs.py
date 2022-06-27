class ExpandTabsTest(UnitTest):
    @data_provider(
        [
            ("\t", " " * 8),
            ("\t\t", " " * 16),
            ("    \t", " " * 8),
            ("\t    ", " " * 12),
            ("abcd\t", "abcd    "),
            ("abcdefg\t", "abcdefg "),
            ("abcdefgh\t", "abcdefgh        "),
            ("\tsuffix", "        suffix"),
        ]
    )
    def test_expand_tabs(self, input: str, output: str) -> None:
        self.assertEqual(expand_tabs(input), output)