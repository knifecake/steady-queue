def flatten(iterable):
    result = []
    for item in iterable:
        if isinstance(item, list):
            result.extend(item)
        else:
            result.append(item)
    return result


def flat_map(func, *iterables):
    return flatten(map(func, *iterables))


def compact(iterable):
    return filter(None, iterable)
