class _Node:
    __slots__ = ("key", "value", "next")

    def __init__(self, key, value, next_node=None):
        self.key = key
        self.value = value
        self.next = next_node


class HashTable:
    """A string-keyed hash table using Horner hashing and separate chaining."""

    def __init__(self, bucket_count=16):
        if (
            not isinstance(bucket_count, int)
            or isinstance(bucket_count, bool)
            or bucket_count <= 0
        ):
            raise ValueError("bucket_count must be a positive integer")

        self.bucket_count = bucket_count
        self.buckets = [None] * bucket_count
        self._size = 0

    @property
    def load_factor(self):
        return self._size / self.bucket_count

    def hash_index(self, key):
        if not isinstance(key, str):
            raise ValueError("key must be a string")

        index = 0
        for character in key:
            index = (31 * index + ord(character)) % self.bucket_count
        return index

    def put(self, key, value):
        index = self.hash_index(key)
        node = self.buckets[index]

        while node is not None:
            if node.key == key:
                node.value = value
                return
            node = node.next

        self.buckets[index] = _Node(key, value, self.buckets[index])
        self._size += 1

    def get(self, key, default=None):
        index = self.hash_index(key)
        node = self.buckets[index]

        while node is not None:
            if node.key == key:
                return node.value
            node = node.next

        return default

    def contains(self, key):
        index = self.hash_index(key)
        node = self.buckets[index]

        while node is not None:
            if node.key == key:
                return True
            node = node.next

        return False

    def __contains__(self, key):
        return self.contains(key)

    def __len__(self):
        return self._size

    def items(self):
        for bucket in self.buckets:
            node = bucket
            while node is not None:
                yield node.key, node.value
                node = node.next
