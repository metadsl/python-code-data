def test_funcdef(self):
    def d01(a=1):
        pass

    d01(1)
    d01(*(1,))
