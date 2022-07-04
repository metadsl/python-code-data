def count_between_floats(x, y, width=64):
    assert x <= y
    if is_negative(x):
        if is_negative(y):
            return float_to_int(x, width) - float_to_int(y, width) + 1
        else:
            return count_between_floats(x, -0.0, width) + count_between_floats(
                0.0, y, width
            )