# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Melody

import unittest

from melody.helpers._dataclass import Media
from melody.helpers._queue import Queue


def _item(suffix: str) -> Media:
    return Media(
        id=f"id-{suffix}",
        duration="3:00",
        duration_sec=180,
        file_path=f"/tmp/{suffix}.mp3",
        message_id=0,
        url=f"https://example.com/{suffix}",
        title=suffix,
        video=False,
    )


class QueueTest(unittest.TestCase):
    def setUp(self):
        self.q = Queue()

    def test_add_returns_zero_based_index(self):
        self.assertEqual(self.q.add(1, _item("a")), 0)
        self.assertEqual(self.q.add(1, _item("b")), 1)

    def test_get_current_and_next(self):
        self.q.add(1, _item("a"))
        self.q.add(1, _item("b"))
        self.assertEqual(self.q.get_current(1).id, "id-a")
        # check=True peeks without popping.
        self.assertEqual(self.q.get_next(1, check=True).id, "id-b")
        self.assertEqual(self.q.get_current(1).id, "id-a")
        # Default pops current.
        self.assertEqual(self.q.get_next(1).id, "id-b")
        self.assertEqual(self.q.get_next(1), None)

    def test_get_next_empty(self):
        self.assertEqual(self.q.get_next(42), None)
        self.assertEqual(self.q.get_current(42), None)

    def test_check_item(self):
        self.q.add(1, _item("a"))
        self.q.add(1, _item("b"))
        pos, track = self.q.check_item(1, "id-b")
        self.assertEqual((pos, track.id), (1, "id-b"))
        self.assertEqual(self.q.check_item(1, "missing"), (-1, None))

    def test_force_add_replaces_current(self):
        self.q.add(1, _item("a"))
        self.q.add(1, _item("b"))
        self.q.force_add(1, _item("f"))
        self.assertEqual(self.q.get_current(1).id, "id-f")
        self.assertEqual([t.id for t in self.q.get_queue(1)], ["id-f", "id-b"])

    def test_force_add_with_remove(self):
        for s in "abcd":
            self.q.add(1, _item(s))
        # Replace now playing, removing the item at index 2 ("c").
        self.q.force_add(1, _item("f"), remove=2)
        self.assertEqual([t.id for t in self.q.get_queue(1)], ["id-f", "id-b", "id-d"])

    def test_clear_empties_queue(self):
        self.q.add(1, _item("a"))
        self.q.clear(1)
        self.assertEqual(self.q.size(1), 0)
        self.assertEqual(self.q.get_current(1), None)

    def test_queues_are_independent(self):
        self.q.add(1, _item("a"))
        self.q.add(2, _item("b"))
        self.assertEqual(self.q.get_current(1).id, "id-a")
        self.assertEqual(self.q.get_current(2).id, "id-b")


if __name__ == "__main__":
    unittest.main()
