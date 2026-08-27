"""
Multi-Domain Scheduler
Rebuild 2: Scheduler Domain Lanes

Defines the scheduler lanes:
  - cognitive lane
  - orchestration lane
  - substrate lane
  - governance lane

Each lane is a priority queue that processes messages deterministically.
"""

from typing import Dict, List, Any, Enum, Callable, Optional
from dataclasses import dataclass
from collections import deque
import time


class SchedulerLane(Enum):
    """Scheduler domain lanes"""
    COGNITIVE = "cognitive"
    ORCHESTRATION = "orchestration"
    SUBSTRATE = "substrate"
    GOVERNANCE = "governance"


@dataclass
class ScheduledMessage:
    """A message queued for processing"""
    id: str
    lane: SchedulerLane
    priority: int
    payload: Dict[str, Any]
    timestamp: float
    max_age_ms: int = 30000
    
    def is_stale(self) -> bool:
        """Check if message has exceeded max age"""
        age_ms = (time.time() - self.timestamp) * 1000
        return age_ms > self.max_age_ms


class DomainLane:
    """
    A single scheduler lane (priority queue).
    Processes messages for a specific domain.
    """
    
    def __init__(self, name: SchedulerLane, max_queue_size: int = 10000):
        self.name = name
        self.queue: deque[ScheduledMessage] = deque()
        self.max_queue_size = max_queue_size
        self.processed_count = 0
        self.dropped_count = 0
    
    def enqueue(self, msg: ScheduledMessage) -> bool:
        """Add message to lane queue"""
        if len(self.queue) >= self.max_queue_size:
            print(f"[SCHEDULER] {self.name.value} lane full, dropping message")
            self.dropped_count += 1
            return False
        
        self.queue.append(msg)
        return True
    
    def dequeue(self) -> Optional[ScheduledMessage]:
        """Get next message from lane"""
        if not self.queue:
            return None
        
        # TODO: Implement priority-based dequeue
        # For now, FIFO
        msg = self.queue.popleft()
        
        if msg.is_stale():
            print(f"[SCHEDULER] Dropping stale message in {self.name.value} lane")
            self.dropped_count += 1
            return None
        
        return msg
    
    def size(self) -> int:
        """Queue size"""
        return len(self.queue)
    
    def stats(self) -> Dict[str, Any]:
        """Lane statistics"""
        return {
            "name": self.name.value,
            "queue_size": self.size(),
            "processed": self.processed_count,
            "dropped": self.dropped_count,
        }


class MultiDomainScheduler:
    """
    Kernel scheduler that manages 4 domain lanes.
    
    Each lane processes messages independently but respects shared invariants:
      - No deadlock between lanes
      - Message ordering within lanes
      - Cycle completion guarantee
    """
    
    def __init__(self, cycle_ms: int = 100):
        self.cycle_ms = cycle_ms
        self.lanes: Dict[SchedulerLane, DomainLane] = {
            SchedulerLane.COGNITIVE: DomainLane(SchedulerLane.COGNITIVE),
            SchedulerLane.ORCHESTRATION: DomainLane(SchedulerLane.ORCHESTRATION),
            SchedulerLane.SUBSTRATE: DomainLane(SchedulerLane.SUBSTRATE),
            SchedulerLane.GOVERNANCE: DomainLane(SchedulerLane.GOVERNANCE),
        }
        
        self.handlers: Dict[SchedulerLane, Callable] = {}
        self.running = False
    
    def register_handler(self, lane: SchedulerLane, handler: Callable) -> None:
        """Register a message handler for a lane"""
        self.handlers[lane] = handler
    
    def submit(self, lane: SchedulerLane, msg: ScheduledMessage) -> bool:
        """Submit a message to a lane"""
        if lane not in self.lanes:
            raise ValueError(f"Unknown lane: {lane}")
        
        return self.lanes[lane].enqueue(msg)
    
    def cycle(self) -> int:
        """
        Execute one scheduler cycle.
        
        Process one message from each lane in round-robin fashion.
        Returns number of messages processed.
        """
        start_time = time.time()
        processed = 0
        
        # Round-robin through lanes
        for lane in SchedulerLane:
            if lane not in self.lanes:
                continue
            
            domain_lane = self.lanes[lane]
            msg = domain_lane.dequeue()
            
            if msg is None:
                continue
            
            # Route to handler
            if lane in self.handlers:
                try:
                    self.handlers[lane](msg)
                    domain_lane.processed_count += 1
                    processed += 1
                except Exception as e:
                    print(f"[SCHEDULER] Handler error in {lane.value}: {e}")
                    domain_lane.dropped_count += 1
        
        # Check cycle time
        cycle_time_ms = (time.time() - start_time) * 1000
        if cycle_time_ms > self.cycle_ms:
            print(f"[SCHEDULER] Cycle exceeded budget: {cycle_time_ms:.1f}ms > {self.cycle_ms}ms")
        
        return processed
    
    def run(self) -> None:
        """
        Start scheduler loop.
        Runs until stopped.
        """
        print("[SCHEDULER] Starting multi-domain scheduler")
        self.running = True
        
        cycle_count = 0
        while self.running:
            processed = self.cycle()
            cycle_count += 1
            
            if cycle_count % 10 == 0:
                self._log_stats()
            
            # Sleep to maintain cycle time
            time.sleep(self.cycle_ms / 1000.0)
    
    def stop(self) -> None:
        """Stop scheduler"""
        self.running = False
        print("[SCHEDULER] Scheduler stopped")
    
    def _log_stats(self) -> None:
        """Log lane statistics"""
        print("\n[SCHEDULER] Lane stats:")
        for lane in SchedulerLane:
            if lane in self.lanes:
                stats = self.lanes[lane].stats()
                print(f"  {stats['name']}: queue={stats['queue_size']}, processed={stats['processed']}, dropped={stats['dropped']}")


class SchedulerCoordinator:
    """
    Coordinates multiple scheduler instances.
    Handles cross-lane dependencies and deadlock prevention.
    """
    
    def __init__(self):
        self.schedulers: List[MultiDomainScheduler] = []
    
    def add_scheduler(self, scheduler: MultiDomainScheduler) -> None:
        """Add a scheduler to coordinate"""
        self.schedulers.append(scheduler)
    
    def check_deadlock(self) -> bool:
        """
        Check if any lane is deadlocked.
        
        Simple heuristic: if a lane has messages but hasn't
        processed any for N cycles, it's likely deadlocked.
        """
        # TODO: Implement deadlock detection
        return False
