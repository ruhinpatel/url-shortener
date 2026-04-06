import re

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)  # 62


def encode(num: int) -> str:
    """Encode a positive integer to a base62 string."""
    if num == 0:
        return ALPHABET[0]
    result = []
    while num:
        result.append(ALPHABET[num % BASE])
        num //= BASE
    return "".join(reversed(result))


def decode(s: str) -> int:
    """Decode a base62 string back to an integer."""
    result = 0
    for char in s:
        result = result * BASE + ALPHABET.index(char)
    return result


def is_valid_custom_code(code: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9]{3,20}$", code))
