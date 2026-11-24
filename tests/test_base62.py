
import unittest

from src.base62 import encode, decode


class TestBase62(unittest.TestCase):

    def test_encode_basic(self):
        self.assertEqual(encode(0), "0")
        self.assertEqual(encode(9), "9")
        self.assertEqual(encode(10), "a")
        self.assertEqual(encode(35), "z")
        self.assertEqual(encode(36), "A")
        self.assertEqual(encode(61), "Z")
        self.assertEqual(encode(62), "10")

    def test_decode_basic(self):
        self.assertEqual(decode("0"), 0)
        self.assertEqual(decode("9"), 9)
        self.assertEqual(decode("a"), 10)
        self.assertEqual(decode("z"), 35)
        self.assertEqual(decode("A"), 36)
        self.assertEqual(decode("Z"), 61)
        self.assertEqual(decode("10"), 62)

    def test_round_trip(self):
        numbers = [0, 1, 10, 61, 62, 100, 999, 123456789]

        for n in numbers:
            self.assertEqual(decode(encode(n)), n)

    def test_invalid_encode(self):
        for n in [-1, 1.5, "62", True]:
            with self.assertRaises(ValueError):
                encode(n)

    def test_invalid_decode(self):
        for s in ["", "!", "hello world", "abc_"]:
            with self.assertRaises(ValueError):
                decode(s)


if __name__ == "__main__":
    unittest.main()

