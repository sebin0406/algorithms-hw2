import unittest

from src.hash_table import HashTable


class TestHashTable(unittest.TestCase):

    def test_empty_table(self):
        table = HashTable(bucket_count=4)

        self.assertEqual(len(table), 0)
        self.assertEqual(table.load_factor, 0)
        self.assertFalse(table.contains("missing"))
        self.assertIsNone(table.get("missing"))

    def test_insert_and_lookup(self):
        table = HashTable(bucket_count=4)
        table.put("url", "code")

        self.assertTrue(table.contains("url"))
        self.assertEqual(table.get("url"), "code")
        self.assertEqual(len(table), 1)
        self.assertEqual(table.load_factor, 0.25)

    def test_collision_chain_and_update(self):
        table = HashTable(bucket_count=1)
        table.put("first", "1")
        table.put("middle", "2")
        table.put("last", "3")

        self.assertEqual(table.get("first"), "1")
        self.assertEqual(table.get("middle"), "2")
        self.assertEqual(table.get("last"), "3")
        self.assertEqual(len(table), 3)

        table.put("middle", "updated")

        self.assertEqual(table.get("middle"), "updated")
        self.assertEqual(len(table), 3)
        self.assertEqual(table.load_factor, 3)

    def test_horner_hash_uses_bucket_count(self):
        table = HashTable(bucket_count=7)
        expected = 0
        for character in "abc":
            expected = (31 * expected + ord(character)) % 7

        self.assertEqual(table.hash_index("abc"), expected)

    def test_invalid_bucket_count(self):
        for bucket_count in [0, -1, 1.5, True]:
            with self.subTest(bucket_count=bucket_count):
                with self.assertRaises(ValueError):
                    HashTable(bucket_count=bucket_count)


if __name__ == "__main__":
    unittest.main()
