"""
Utility module for general-purpose data processing and math operations.

This module provides helper functions for numeric computation, string
manipulation, and collection processing. All public functions are documented
and intended for use in production pipelines.
"""

import math
from typing import Any


# ---------------------------------------------------------------------------
# Section 1: Basic numeric utilities
# ---------------------------------------------------------------------------


def square(n: float) -> float:
    """Return the square of n."""
    return n * n


def cube(n: float) -> float:
    """Return the cube of n."""
    return n * n * n


def is_even(n: int) -> bool:
    """Return True if n is even."""
    return n % 2 == 0


def is_odd(n: int) -> bool:
    """Return True if n is odd."""
    return n % 2 != 0


def clamp(value: float, lo: float, hi: float) -> float:
    """Clamp value to the range [lo, hi]."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def sign(n: float) -> int:
    """Return -1, 0, or 1 depending on the sign of n."""
    if n < 0:
        return -1
    if n > 0:
        return 1
    return 0


def absolute(n: float) -> float:
    """Return the absolute value of n without using abs()."""
    return n if n >= 0 else -n


# ---------------------------------------------------------------------------
# Section 2: Bug 1 — calculate_discount
# ---------------------------------------------------------------------------


def calculate_discount(price: float, percentage: float) -> float:
    """Return the discounted price after applying the given percentage discount.

    Example: calculate_discount(100, 20) should return 80.0
    """
    # BUG: sollte Rabatt abziehen, nicht addieren
    return price + percentage


# ---------------------------------------------------------------------------
# Section 3: String utilities
# ---------------------------------------------------------------------------


def to_upper(s: str) -> str:
    """Return s converted to uppercase."""
    return s.upper()


def to_lower(s: str) -> str:
    """Return s converted to lowercase."""
    return s.lower()


def strip_spaces(s: str) -> str:
    """Return s with leading and trailing whitespace removed."""
    return s.strip()


def capitalize_words(s: str) -> str:
    """Return s with the first letter of each word capitalized."""
    return " ".join(word.capitalize() for word in s.split())


def count_vowels(s: str) -> int:
    """Return the number of vowels in s (case-insensitive)."""
    return sum(1 for c in s.lower() if c in "aeiou")


def repeat_string(s: str, times: int) -> str:
    """Return s repeated times times."""
    return s * times


# ---------------------------------------------------------------------------
# Section 4: Bug 2 — is_palindrome
# ---------------------------------------------------------------------------


def is_palindrome(s: str) -> bool:
    """Return True if s reads the same forwards and backwards.

    Example: is_palindrome('racecar') should return True
             is_palindrome('hello')   should return False
    """
    # BUG: vergleicht string mit sich selbst, gibt immer True zurueck
    return s == s


# ---------------------------------------------------------------------------
# Section 5: More numeric helpers
# ---------------------------------------------------------------------------


def factorial(n: int) -> int:
    """Return n! (n factorial). n must be >= 0."""
    if n < 0:
        raise ValueError("factorial requires n >= 0")
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def gcd(a: int, b: int) -> int:
    """Return the greatest common divisor of a and b."""
    while b:
        a, b = b, a % b
    return a


def lcm(a: int, b: int) -> int:
    """Return the least common multiple of a and b."""
    return abs(a * b) // gcd(a, b) if a and b else 0


def is_prime(n: int) -> bool:
    """Return True if n is a prime number."""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(math.sqrt(n)) + 1, 2):
        if n % i == 0:
            return False
    return True


def power(base: float, exp: int) -> float:
    """Return base raised to the power exp (integer exponent)."""
    result = 1.0
    negative = exp < 0
    exp = abs(exp)
    for _ in range(exp):
        result *= base
    return 1.0 / result if negative else result


# ---------------------------------------------------------------------------
# Section 6: Bug 3 — flatten_list
# ---------------------------------------------------------------------------


def flatten_list(nested: list) -> list:
    """Return a flat list containing all elements from a nested list structure.

    Example: flatten_list([1, [2, [3, 4]], 5]) should return [1, 2, 3, 4, 5]
    """
    # BUG: rekursion fehlt, gibt einfach nested unveraendert zurueck
    return nested


# ---------------------------------------------------------------------------
# Section 7: Collection helpers
# ---------------------------------------------------------------------------


def unique_items(items: list) -> list:
    """Return a list with duplicates removed, preserving original order."""
    seen: set = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def chunk_list(items: list, size: int) -> list:
    """Split items into chunks of length size."""
    return [items[i:i + size] for i in range(0, len(items), size)]


def zip_dicts(keys: list, values: list) -> dict:
    """Return a dict built from parallel keys and values lists."""
    return dict(zip(keys, values))


def flatten_dict(d: dict, prefix: str = "") -> dict:
    """Flatten a nested dict using dot-notation keys."""
    result: dict = {}
    for k, v in d.items():
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            result.update(flatten_dict(v, full_key))
        else:
            result[full_key] = v
    return result


# ---------------------------------------------------------------------------
# Section 8: Bug 4 — safe_divide
# ---------------------------------------------------------------------------


def safe_divide(a: float, b: float) -> float:
    """Return a / b. Returns 0.0 if b is zero instead of raising an error.

    Example: safe_divide(10, 0) should return 0.0
             safe_divide(10, 2) should return 5.0
    """
    # BUG: crasht bei b=0, kein try/except und kein if-check
    return a / b


# ---------------------------------------------------------------------------
# Section 9: More string helpers
# ---------------------------------------------------------------------------


def truncate(s: str, max_len: int, suffix: str = "...") -> str:
    """Return s truncated to max_len characters, appending suffix if truncated."""
    if len(s) <= max_len:
        return s
    return s[:max_len - len(suffix)] + suffix


def pad_left(s: str, width: int, char: str = " ") -> str:
    """Return s left-padded with char to at least width characters."""
    return s.rjust(width, char)


def pad_right(s: str, width: int, char: str = " ") -> str:
    """Return s right-padded with char to at least width characters."""
    return s.ljust(width, char)


def slugify(s: str) -> str:
    """Return a lowercase slug with spaces replaced by hyphens."""
    return "-".join(s.lower().split())


def remove_duplicates_str(items: list) -> list:
    """Return list of strings with case-insensitive duplicates removed."""
    seen: set = set()
    result = []
    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


# ---------------------------------------------------------------------------
# Section 10: Bug 5 — word_count
# ---------------------------------------------------------------------------


def word_count(text: str) -> int:
    """Return the number of words in text (words are separated by whitespace).

    Example: word_count('hello world foo') should return 3
    """
    # BUG: zaehlt Zeichen statt Woerter
    return len(text)


# ---------------------------------------------------------------------------
# Section 11: Dict and mapping helpers
# ---------------------------------------------------------------------------


def invert_dict(d: dict) -> dict:
    """Return a new dict with keys and values swapped."""
    return {v: k for k, v in d.items()}


def filter_dict(d: dict, keys: list) -> dict:
    """Return a new dict containing only the specified keys."""
    return {k: v for k, v in d.items() if k in keys}


def deep_get(d: dict, *keys: str, default: Any = None) -> Any:
    """Safely retrieve a value from a nested dict using a sequence of keys."""
    current = d
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
        if current is default:
            return default
    return current


# ---------------------------------------------------------------------------
# Section 12: Bug 6 — merge_dicts
# ---------------------------------------------------------------------------


def merge_dicts(a: dict, b: dict) -> dict:
    """Return a new dict that merges a and b. Keys in b override keys in a.

    Example: merge_dicts({'x': 1}, {'y': 2}) should return {'x': 1, 'y': 2}
    """
    # BUG: b wird ignoriert, gibt nur a zurueck
    return a


# ---------------------------------------------------------------------------
# Section 13: Sorting and comparison helpers
# ---------------------------------------------------------------------------


def min_of_three(a: float, b: float, c: float) -> float:
    """Return the smallest of three values."""
    result = a
    if b < result:
        result = b
    if c < result:
        result = c
    return result


def max_of_three(a: float, b: float, c: float) -> float:
    """Return the largest of three values."""
    result = a
    if b > result:
        result = b
    if c > result:
        result = c
    return result


def sorted_unique(items: list) -> list:
    """Return a sorted list with duplicates removed."""
    return sorted(set(items))


def running_average(values: list) -> list:
    """Return a list of running averages for the input sequence."""
    result = []
    total = 0.0
    for i, v in enumerate(values, 1):
        total += v
        result.append(total / i)
    return result


# ---------------------------------------------------------------------------
# Section 14: Bug 7 — reverse_words
# ---------------------------------------------------------------------------


def reverse_words(sentence: str) -> str:
    """Return the sentence with the order of words reversed.

    Example: reverse_words('hello world foo') should return 'foo world hello'
    """
    # BUG: Zeichenkette statt Woerter umgekehrt (kehrt jeden Buchstaben um)
    return sentence[::-1]


# ---------------------------------------------------------------------------
# Section 15: Validation helpers
# ---------------------------------------------------------------------------


def is_valid_email(email: str) -> bool:
    """Return True if email contains exactly one '@' and at least one '.'."""
    parts = email.split("@")
    if len(parts) != 2:
        return False
    local, domain = parts
    return bool(local) and "." in domain


def is_valid_url(url: str) -> bool:
    """Return True if url starts with http:// or https://."""
    return url.startswith("http://") or url.startswith("https://")


def is_positive(n: float) -> bool:
    """Return True if n is strictly positive."""
    return n > 0


def is_integer_string(s: str) -> bool:
    """Return True if s represents a valid integer (possibly negative)."""
    try:
        int(s)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Section 16: Bug 8 — fibonacci
# ---------------------------------------------------------------------------


def fibonacci(n: int) -> int:
    """Return the n-th Fibonacci number (0-indexed).

    fibonacci(0) = 0
    fibonacci(1) = 1
    fibonacci(6) = 8

    Example: fibonacci(6) should return 8
    """
    # BUG: quadriert n statt Fibonacci-Sequenz zu berechnen
    return n * n


# ---------------------------------------------------------------------------
# Section 17: Miscellaneous helpers
# ---------------------------------------------------------------------------


def percentage(part: float, whole: float) -> float:
    """Return what percentage part is of whole. Returns 0.0 if whole is zero."""
    if whole == 0:
        return 0.0
    return (part / whole) * 100.0


def celsius_to_fahrenheit(c: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return c * 9.0 / 5.0 + 32.0


def fahrenheit_to_celsius(f: float) -> float:
    """Convert Fahrenheit to Celsius."""
    return (f - 32.0) * 5.0 / 9.0


def rotate_list(items: list, steps: int) -> list:
    """Rotate list to the right by steps positions."""
    if not items:
        return items
    steps = steps % len(items)
    return items[-steps:] + items[:-steps] if steps else list(items)


def group_by(items: list, key_fn) -> dict:
    """Group items by the result of key_fn(item). Returns dict of lists."""
    result: dict = {}
    for item in items:
        k = key_fn(item)
        result.setdefault(k, []).append(item)
    return result


def transpose_matrix(matrix: list) -> list:
    """Transpose a 2D list (list of rows -> list of columns)."""
    if not matrix or not matrix[0]:
        return []
    rows = len(matrix)
    cols = len(matrix[0])
    return [[matrix[r][c] for r in range(rows)] for c in range(cols)]


def moving_sum(values: list, window: int) -> list:
    """Return a list of moving sums with the given window size."""
    result = []
    for i in range(len(values) - window + 1):
        result.append(sum(values[i:i + window]))
    return result
