"""
Are there any additional freevars or cellvars?
"""
import dis

from rich import pretty

from code_data.module_codes import all_module_code_data

pretty.install()

cd = all_module_code_data()


print("additional cellvars", any(c._additional_cellvars for c in cd))
# no
print("additional freevars", any(c._additional_freevars for c in cd))
# yes
# When does it come up?
next(filter(lambda c: c._additional_freevars, cd))
# Additional freevar here of __class__

# def run(
#     self, result: Optional[unittest.TestResult] = None
# ) -> Optional[unittest.TestResult]:
#     ret = super().run(result)
#     # As a last resort, if an exception escaped super.run() and wasn't
#     # re-raised in tearDown, raise it here.  This will cause the
#     # unittest run to fail messily, but that's better than silently
#     # ignoring an error.
#     self.__rethrow()
#     return ret

# Why is this? Does it happen for every method?


class A:
    def x(self):
        super().x()  # type: ignore


dis.show_code(A.x)

# Ok it shows up with super!
# What if we remove it, will it ruin the call?


class C:
    def c(self):
        return "super"


class B(C):
    def b(self):
        return super().c()


assert B().b() == "super"

# Includes __class__
dis.show_code(B.b)

B.b.__code__ = B.b.__code__.replace(co_freevars=())
# This fails:
# ValueError: b() requires a code object with 1 free vars, not 0
dis.dis(
    """class B(C):
    def b(self):
        return super().c()"""
)
# It includes a `LOAD_CLOSURE` which defines the number of freevars we have!
# So we really can't remove extra freevars, even if we want to, without changing how the LOAD_CLOSURE works.
# So should we store the freevars as a list or keep the additional as "unused" but that we can't delete?
# When we had the same thing with args, we just stored them as a list.

# Wait, are there freevars when there aren't a function?


def f():
    x = 1

    class B:
        y = x


dis.show_code(f.__code__.co_consts[2])
# Yes this has a freevar.

# This is true on all Python version we support.
