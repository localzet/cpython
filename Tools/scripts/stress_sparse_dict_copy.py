"""Exercise dict copies across deletion patterns and hash collisions."""

from concurrent.futures import ThreadPoolExecutor
from random import Random


class Key:
    def __init__(self, value):
        self.value = value

    def __hash__(self):
        return self.value % 8

    def __eq__(self, other):
        return self is other


def check_copies(source):
    expected = list(source.items())
    for copy in (source.copy(), dict(source), {**source}):
        if len(copy) != len(expected):
            raise AssertionError("incorrect copied size")
        if any(k is not ek or v is not ev
               for (k, v), (ek, ev) in zip(copy.items(), expected)):
            raise AssertionError("copied keys or values differ")
        if len(copy) != len(source):
            raise AssertionError("copy mutated the source")
        copy.clear()
        if list(source.items()) != expected:
            raise AssertionError("clearing the copy modified the source")


def randomized_checks():
    rng = Random(161524)
    for case in range(1200):
        size = rng.choice((8, 64, 128, 512, 2048))
        if case % 3 == 0:
            keys = [str(i) for i in range(size)]
        elif case % 3 == 1:
            keys = list(range(size))
        else:
            keys = [Key(i) for i in range(size)]

        source = {key: object() for key in keys}
        rng.shuffle(keys)
        for key in keys[:rng.randrange(size + 1)]:
            del source[key]

        for key in keys[:rng.randrange(size + 1)]:
            source[key] = object()

        check_copies(source)


def concurrent_checks():
    source = dict.fromkeys(range(3000))
    for key in range(2000):
        del source[key]
    expected = list(source.items())

    def worker(_):
        for _ in range(300):
            check_copies(source)
        return True

    with ThreadPoolExecutor(max_workers=4) as executor:
        if not all(executor.map(worker, range(4))):
            raise AssertionError("concurrent copy failed")
    if list(source.items()) != expected:
        raise AssertionError("concurrent copies modified the source")


if __name__ == "__main__":
    randomized_checks()
    concurrent_checks()
    print("sparse dictionary stress checks passed")
