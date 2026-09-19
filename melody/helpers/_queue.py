# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Melody


from collections import defaultdict, deque

from ._dataclass import Media, Track

MediaItem = Media | Track


class Queue:
    def __init__(self):
        self.queues: dict[int, deque[MediaItem]] = defaultdict(deque)

    def add(self, chat_id: int, item: MediaItem) -> int:
        """Add an item to the queue and return its 0-based index (0 = now playing)."""
        self.queues[chat_id].append(item)
        return len(self.queues[chat_id]) - 1

    def size(self, chat_id: int) -> int:
        """O(1) length; get_queue() copies the deque."""
        return len(self.queues[chat_id])

    def check_item(self, chat_id: int, item_id: str) -> tuple[int, MediaItem | None]:
        """Find an item by ID; (-1, None) if absent."""
        pos, track = next(
            (
                (i, track)
                for i, track in enumerate(list(self.queues[chat_id]))
                if track.id == item_id
            ),
            (-1, None),
        )
        return pos, track

    def force_add(
        self, chat_id: int, item: MediaItem, remove: int | bool = False
    ) -> None:
        """Replace the currently playing item with a new one."""
        self.remove_current(chat_id)
        self.queues[chat_id].appendleft(item)
        if remove:
            self.queues[chat_id].rotate(-remove)
            self.queues[chat_id].popleft()
            self.queues[chat_id].rotate(remove)

    def get_current(self, chat_id: int) -> MediaItem | None:
        """First item (now playing), if any."""
        return self.queues[chat_id][0] if self.queues[chat_id] else None

    def get_next(self, chat_id: int, check: bool = False) -> MediaItem | None:
        """Pop current and return next; check=True only peeks."""
        if not self.queues[chat_id]:
            return None
        if check:
            return self.queues[chat_id][1] if len(self.queues[chat_id]) > 1 else None

        self.queues[chat_id].popleft()
        return self.queues[chat_id][0] if self.queues[chat_id] else None

    def get_queue(self, chat_id: int) -> list[MediaItem]:
        """Full queue including now playing."""
        return list(self.queues[chat_id])

    def set_queue(self, chat_id: int, items: list[MediaItem]) -> None:
        """Replace queue contents."""
        self.queues[chat_id] = deque(items)

    def remove_current(self, chat_id: int) -> None:
        """Drop now playing, if any."""
        if self.queues[chat_id]:
            self.queues[chat_id].popleft()

    def clear(self, chat_id: int) -> None:
        """Empty the queue."""
        self.queues[chat_id].clear()
