"""
Message Queue
Rebuild 3: Async Message Processing

Queues messages for async processing.
Integrates with scheduler lanes.
"""

from typing import Dict, Any, Optional, Callable
from collections import deque
from dataclasses import dataclass
import uuid


@dataclass
class QueuedMessage:
    """A message in the queue"""
    id: str
    source: str
    payload: Dict[str, Any]
    handler: Optional[Callable] = None
    priority: int = 0
    retry_count: int = 0
    max_retries: int = 3


class MessageQueue:
    """
    Queue for async message processing.
    Integrates with kernel scheduler.
    """
    
    def __init__(self, max_size: int = 10000):
        self.queue: deque = deque()
        self.max_size = max_size
        self.processed_count = 0
    
    def enqueue(self, message: QueuedMessage) -> bool:
        """
        Enqueue a message for processing.
        Returns success.
        """
        if len(self.queue) >= self.max_size:
            print("[QUEUE] Queue full, dropping message")
            return False
        
        self.queue.append(message)
        return True
    
    def dequeue(self) -> Optional[QueuedMessage]:
        """
        Dequeue next message.
        Returns highest priority message if available.
        """
        if not self.queue:
            return None
        
        # TODO: Implement priority-based dequeue
        # For now, simple FIFO
        return self.queue.popleft()
    
    def size(self) -> int:
        """Queue size"""
        return len(self.queue)
    
    def process_all(self) -> int:
        """
        Process all queued messages.
        Returns count processed.
        """
        count = 0
        while self.queue:
            msg = self.dequeue()
            if msg and msg.handler:
                try:
                    msg.handler(msg.payload)
                    self.processed_count += 1
                    count += 1
                except Exception as e:
                    print(f"[QUEUE] Handler error: {e}")
                    msg.retry_count += 1
                    if msg.retry_count < msg.max_retries:
                        self.enqueue(msg)  # Retry
        
        return count
