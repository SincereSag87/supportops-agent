from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter


@contextmanager
def timer() -> Iterator[callable]:
    start = perf_counter()

    def elapsed_ms() -> float:
        return round((perf_counter() - start) * 1000, 2)

    yield elapsed_ms
