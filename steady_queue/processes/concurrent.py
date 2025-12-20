from threading import Lock


class AtomicInteger:
    def __init__(self, initial_value: int = 0):
        self._value = initial_value
        self._lock = Lock()

    @property
    def value(self) -> int:
        with self._lock:
            return self._value

    def increment(self) -> int:
        with self._lock:
            self._value += 1
            return self._value

    def decrement(self) -> int:
        with self._lock:
            self._value -= 1
            return self._value


class Dict:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lock = Lock()
        self._dict = dict(*args, **kwargs)

    def __getitem__(self, key):
        with self._lock:
            return self._dict[key]

    def __setitem__(self, key, value):
        with self._lock:
            self._dict[key] = value

    def __delitem__(self, key):
        with self._lock:
            del self._dict[key]

    def values(self):
        with self._lock:
            return list(self._dict.values())

    def clear(self):
        with self._lock:
            self._dict.clear()
