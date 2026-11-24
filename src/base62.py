
ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = 62


def encode(n):
    """0 이상의 정수를 Base62 문자열로 변환한다."""
    if not isinstance(n, int) or isinstance(n, bool) or n < 0:
        raise ValueError("n must be a non-negative integer")

    if n == 0:
        return "0"

    digits = []

    while n > 0:
        remainder = n % BASE
        digits.append(ALPHABET[remainder])
        n //= BASE

    return "".join(reversed(digits))


def decode(s):
    """Base62 문자열을 정수로 변환한다."""
    if not isinstance(s, str) or not s:
        raise ValueError("s must be a non-empty string")

    result = 0

    for char in s:
        value = ALPHABET.find(char)

        if value == -1:
            raise ValueError(f"invalid Base62 character: {char}")

        result = result * BASE + value

    return result
