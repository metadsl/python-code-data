class SpecSignatureTest(unittest.TestCase):

    def _check_someclass_mock(self, mock):
        self.assertRaises(AttributeError, getattr, mock, 'foo')
        mock.one(1, 2)
        mock.one.assert_called_with(1, 2)
        self.assertRaises(AssertionError,
                          mock.one.assert_called_with, 3, 4)
        self.assertRaises(TypeError, mock.one, 1)

        mock.two()
        mock.two.assert_called_with()
        self.assertRaises(AssertionError,
                          mock.two.assert_called_with, 3)
        self.assertRaises(TypeError, mock.two, 1)

        mock.three()
        mock.three.assert_called_with()
        self.assertRaises(AssertionError,
                          mock.three.assert_called_with, 3)
        self.assertRaises(TypeError, mock.three, 3, 2)

        mock.three(1)
        mock.three.assert_called_with(1)

        mock.three(a=1)
        mock.three.assert_called_with(a=1)


    def test_basic(self):
        mock = create_autospec(SomeClass)
        self._check_someclass_mock(mock)
        mock = create_autospec(SomeClass())
        self._check_someclass_mock(mock)


    def test_create_autospec_return_value(self):
        def f():
            pass
        mock = create_autospec(f, return_value='foo')
        self.assertEqual(mock(), 'foo')

        class Foo(object):
            pass

        mock = create_autospec(Foo, return_value='foo')
        self.assertEqual(mock(), 'foo')


    def test_autospec_reset_mock(self):
        m = create_autospec(int)
        int(m)
        m.reset_mock()
        self.assertEqual(m.__int__.call_count, 0)


    def test_mocking_unbound_methods(self):
        class Foo(object):
            def foo(self, foo):
                pass
        p = patch.object(Foo, 'foo')
        mock_foo = p.start()
        Foo().foo(1)

        mock_foo.assert_called_with(1)


    def test_create_autospec_unbound_methods(self):
        # see mock issue 128
        # this is expected to fail until the issue is fixed
        return
        class Foo(object):
            def foo(self):
                pass

        klass = create_autospec(Foo)