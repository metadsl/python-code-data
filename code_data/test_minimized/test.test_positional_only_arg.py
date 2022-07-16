class PositionalOnlyTestCase(unittest.TestCase):

    def assertRaisesSyntaxError(self, codestr, regex="invalid syntax"):
        with self.assertRaisesRegex(SyntaxError, regex):
            compile(codestr + "\n", "<test>", "single")

    def test_invalid_syntax_errors(self):
        check_syntax_error(self, "def f(a, b = 5, /, c): pass", "non-default argument follows default argument")
        check_syntax_error(self, "def f(a = 5, b, /, c): pass", "non-default argument follows default argument")
        check_syntax_error(self, "def f(a = 5, b=1, /, c, *, d=2): pass", "non-default argument follows default argument")
        check_syntax_error(self, "def f(a = 5, b, /): pass", "non-default argument follows default argument")
        check_syntax_error(self, "def f(*args, /): pass")
        check_syntax_error(self, "def f(*args, a, /): pass")
        check_syntax_error(self, "def f(**kwargs, /): pass")
        check_syntax_error(self, "def f(/, a = 1): pass")
        check_syntax_error(self, "def f(/, a): pass")
        check_syntax_error(self, "def f(/): pass")
        check_syntax_error(self, "def f(*, a, /): pass")
        check_syntax_error(self, "def f(*, /, a): pass")
        check_syntax_error(self, "def f(a, /, a): pass", "duplicate argument 'a' in function definition")
        check_syntax_error(self, "def f(a, /, *, a): pass", "duplicate argument 'a' in function definition")
        check_syntax_error(self, "def f(a, b/2, c): pass")
        check_syntax_error(self, "def f(a, /, c, /): pass")
        check_syntax_error(self, "def f(a, /, c, /, d): pass")
        check_syntax_error(self, "def f(a, /, c, /, d, *, e): pass")
        check_syntax_error(self, "def f(a, *, c, /, d, e): pass")

    def test_invalid_syntax_errors_async(self):
        check_syntax_error(self, "async def f(a, b = 5, /, c): pass", "non-default argument follows default argument")
        check_syntax_error(self, "async def f(a = 5, b, /, c): pass", "non-default argument follows default argument")
        check_syntax_error(self, "async def f(a = 5, b=1, /, c, d=2): pass", "non-default argument follows default argument")
        check_syntax_error(self, "async def f(a = 5, b, /): pass", "non-default argument follows default argument")
        check_syntax_error(self, "async def f(*args, /): pass")
        check_syntax_error(self, "async def f(*args, a, /): pass")
        check_syntax_error(self, "async def f(**kwargs, /): pass")
        check_syntax_error(self, "async def f(/, a = 1): pass")
        check_syntax_error(self, "async def f(/, a): pass")
        check_syntax_error(self, "async def f(/): pass")
        check_syntax_error(self, "async def f(*, a, /): pass")
        check_syntax_error(self, "async def f(*, /, a): pass")
        check_syntax_error(self, "async def f(a, /, a): pass", "duplicate argument 'a' in function definition")
        check_syntax_error(self, "async def f(a, /, *, a): pass", "duplicate argument 'a' in function definition")
        check_syntax_error(self, "async def f(a, b/2, c): pass")
        check_syntax_error(self, "async def f(a, /, c, /): pass")
        check_syntax_error(self, "async def f(a, /, c, /, d): pass")
        check_syntax_error(self, "async def f(a, /, c, /, d, *, e): pass")
        check_syntax_error(self, "async def f(a, *, c, /, d, e): pass")

    def test_optional_positional_only_args(self):
        def f(a, b=10, /, c=100):
            return a + b + c

        self.assertEqual(f(1, 2, 3), 6)
        self.assertEqual(f(1, 2, c=3), 6)
        with self.assertRaisesRegex(TypeError, r"f\(\) got some positional-only arguments passed as keyword arguments: 'b'"):
            f(1, b=2, c=3)

        self.assertEqual(f(1, 2), 103)
        with self.assertRaisesRegex(TypeError, r"f\(\) got some positional-only arguments passed as keyword arguments: 'b'"):
            f(1, b=2)
        self.assertEqual(f(1, c=2), 13)

        def f(a=1, b=10, /, c=100):
            return a + b + c

        self.assertEqual(f(1, 2, 3), 6)
        self.assertEqual(f(1, 2, c=3), 6)
        with self.assertRaisesRegex(TypeError, r"f\(\) got some positional-only arguments passed as keyword arguments: 'b'"):
            f(1, b=2, c=3)

        self.assertEqual(f(1, 2), 103)
        with self.assertRaisesRegex(TypeError, r"f\(\) got some positional-only arguments passed as keyword arguments: 'b'"):
            f(1, b=2)
        self.assertEqual(f(1, c=2), 13)

    def test_syntax_for_many_positional_only(self):
        # more than 255 positional only arguments, should compile ok
        fundef = "def f(%s, /):\n  pass\n" % ', '.join('i%d' % i for i in range(300))
        compile(fundef, "<test>", "single")

    def test_pos_only_definition(self):
        def f(a, b, c, /, d, e=1, *, f, g=2):
            pass

        self.assertEqual(5, f.__code__.co_argcount)  # 3 posonly + 2 "standard args"
        self.assertEqual(3, f.__code__.co_posonlyargcount)
        self.assertEqual((1,), f.__defaults__)

        def f(a, b, c=1, /, d=2, e=3, *, f, g=4):
            pass

        self.assertEqual(5, f.__code__.co_argcount)  # 3 posonly + 2 "standard args"
        self.assertEqual(3, f.__code__.co_posonlyargcount)
        self.assertEqual((1, 2, 3), f.__defaults__)