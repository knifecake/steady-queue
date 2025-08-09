from functools import reduce


def flatten(iterable):
    return list(reduce(lambda x, y: x + y, iterable, []))


def flat_map(func, *iterables):
    return flatten(map(func, *iterables))


def compact(iterable):
    return filter(None, iterable)
