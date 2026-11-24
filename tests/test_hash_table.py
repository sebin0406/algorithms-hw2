import unittest

from src.hash_table import HashTable, LinearProbingHashTable


class TestHashTable(unittest.TestCase):
    table_class = HashTable

    def test_empty_table(self):
        table = self.table_class(bucket_count=4)

        self.assertEqual(len(table), 0)
        self.assertEqual(table.load_factor, 0)
        self.assertFalse(table.contains("missing"))
        self.assertNotIn("missing", table)
        self.assertIsNone(table.get("missing"))
        self.assertIsNone(table.find("missing"))

    def test_insert_and_lookup(self):
        table = self.table_class(bucket_count=4)
        table.put("url", "code")

        self.assertTrue(table.contains("url"))
        self.assertIn("url", table)
        self.assertEqual(table.get("url"), "code")
        self.assertEqual(table.find("url"), "code")
        self.assertEqual(len(table), 1)
        self.assertEqual(table.load_factor, 0.25)

    def test_collisions_and_update(self):
        table = self.table_class(bucket_count=5)
        collision_keys = []
        target_index = table.hash_index("first")
        for number in range(100):
            candidate = f"collision-{number}"
            if table.hash_index(candidate) == target_index:
                collision_keys.append(candidate)
            if len(collision_keys) == 3:
                break

        self.assertEqual(len(collision_keys), 3)
        for index, key in enumerate(collision_keys):
            table.put(key, str(index + 1))

        for index, key in enumerate(collision_keys):
            self.assertEqual(table.get(key), str(index + 1))
        self.assertEqual(len(table), 3)

        table.put(collision_keys[1], "updated")

        self.assertEqual(table.get(collision_keys[1]), "updated")
        self.assertEqual(len(table), 3)
        self.assertEqual(table.load_factor, 0.6)

    def test_horner_hash_uses_bucket_count(self):
        table = self.table_class(bucket_count=7)
        expected = 0
        for character in "abc":
            expected = (31 * expected + ord(character)) % 7

        self.assertEqual(table.hash_index("abc"), expected)

    def test_invalid_bucket_count(self):
        for bucket_count in [0, -1, 1.5, True]:
            with self.subTest(bucket_count=bucket_count):
                with self.assertRaises(ValueError):
                    self.table_class(bucket_count=bucket_count)


class TestLinearProbingHashTable(TestHashTable):
    table_class = LinearProbingHashTable

    def test_consecutive_collisions_are_searched(self):
        table = self.table_class(bucket_count=7)
        keys = []
        target_index = table.hash_index("key-0")
        for number in range(100):
            key = f"key-{number}"
            if table.hash_index(key) == target_index:
                keys.append(key)
            if len(keys) == 4:
                break

        self.assertEqual(len(keys), 4)
        for index, key in enumerate(keys):
            table.put(key, index)

        for index, key in enumerate(keys):
            self.assertEqual(table.get(key), index)

    def test_probe_wraps_from_last_bucket_to_first(self):
        table = self.table_class(bucket_count=5)
        key_at_end = next(
            f"key-{index}"
            for index in range(100)
            if table.hash_index(f"key-{index}") == 4
        )
        key_at_start = next(
            f"start-{index}"
            for index in range(100)
            if table.hash_index(f"start-{index}") == 4
        )

        table.put(key_at_end, "last")
        table.put(key_at_start, "wrapped")

        self.assertEqual(table.buckets[4].key, key_at_end)
        self.assertEqual(table.buckets[0].key, key_at_start)
        self.assertEqual(table.probe_path(key_at_start), [4, 0])
        self.assertEqual(table.get(key_at_start), "wrapped")

    def test_missing_key_and_full_table_are_handled(self):
        table = self.table_class(bucket_count=2)
        table.put("first", 1)
        table.put("second", 2)

        self.assertEqual(len(table), 2)
        self.assertEqual(table.load_factor, 1)
        self.assertFalse(table.contains("missing"))
        self.assertIsNone(table.get("missing"))
        with self.assertRaises(OverflowError):
            table.put("missing", 3)

        table.put("first", "updated")
        self.assertEqual(table.get("first"), "updated")
        self.assertEqual(len(table), 2)


if __name__ == "__main__":
    unittest.main()
