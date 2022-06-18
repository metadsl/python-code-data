def _scan_once(string, idx):
    try:
        nextchar = string[idx]
    except IndexError:
        raise StopIteration(idx) from None

    if nextchar == '"':
        return parse_string(string, idx + 1, strict)
    elif nextchar == "{":
        return parse_object(
            (string, idx + 1),
            strict,
            _scan_once,
            object_hook,
            object_pairs_hook,
            memo,
        )
    elif nextchar == "[":
        return parse_array((string, idx + 1), _scan_once)
    elif nextchar == "n" and string[idx : idx + 4] == "null":
        return None, idx + 4
    elif nextchar == "t" and string[idx : idx + 4] == "true":
        return True, idx + 4
    elif nextchar == "t" and string[idx : idx + 4] == "true":
        return True, idx + 4
