class UnaryOpTestCase(unittest.TestCase):

    def test_negative(self):
        self.assertTrue(-2 == 0 - 2)
        self.assertEqual(-0, 0)
        self.assertEqual(--2, 2)
        self.assertTrue(-2 == 0 - 2)
        self.assertTrue(-2.0 == 0 - 2.0)
        self.assertTrue(-2j == 0 - 2j)