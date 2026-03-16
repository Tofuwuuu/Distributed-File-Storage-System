from collections import deque
from typing import List

from sqlalchemy.orm import Session

from .models import StorageNode


class RoundRobinSelector:
    def __init__(self, nodes: List[StorageNode]):
        self._queue = deque(sorted(nodes, key=lambda n: n.id))

    def pick(self, count: int) -> List[StorageNode]:
        picked: List[StorageNode] = []
        while self._queue and len(picked) < count:
            node = self._queue.popleft()
            picked.append(node)
            self._queue.append(node)
        return picked


def select_nodes(db: Session, replication_factor: int) -> List[StorageNode]:
    nodes = db.query(StorageNode).filter_by(is_active=True).order_by(StorageNode.id).all()
    if len(nodes) < replication_factor:
        raise RuntimeError("Not enough active storage nodes for requested replication factor")
    selector = RoundRobinSelector(nodes)
    return selector.pick(replication_factor)

