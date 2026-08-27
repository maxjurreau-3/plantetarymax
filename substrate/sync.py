"""
Substrate Synchronization
Rebuild 3: State Persistence

Synchronizes Durable Object state with KV store.
Ensures coherence between strong and eventual consistency stores.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import time


@dataclass
class SyncOperation:
    """A sync operation between DO and KV"""
    id: str
    key: str
    source: str  # 'do' or 'kv'
    target: str
    data: Dict[str, Any]
    timestamp: float
    status: str = "pending"


class SubstrateSynchronizer:
    """
    Synchronizes state between Durable Objects and KV store.
    Ensures eventual consistency across both stores.
    """
    
    def __init__(self, do_store, kv_store):
        self.do = do_store
        self.kv = kv_store
        self.sync_log: List[SyncOperation] = []
    
    def sync_do_to_kv(self, key: str) -> bool:
        """
        Sync data from Durable Object to KV.
        DO is source of truth.
        """
        # Read from DO
        do_state = self.do.store.get(key)
        if not do_state:
            return False
        
        # Extract value
        value = do_state.data
        
        # Write to KV
        try:
            self.kv.put(key, value)
            
            # Log sync operation
            self.sync_log.append(
                SyncOperation(
                    id=f"sync_{time.time()}",
                    key=key,
                    source="do",
                    target="kv",
                    data=value,
                    timestamp=time.time(),
                    status="complete",
                )
            )
            return True
        except Exception as e:
            print(f"[SUBSTRATE] DO→KV sync failed: {e}")
            return False
    
    def sync_kv_to_do(self, key: str) -> bool:
        """
        Sync data from KV to Durable Object.
        Used for recovery or replication.
        """
        # Read from KV
        kv_state = self.kv.get(key)
        if not kv_state:
            return False
        
        # Write to DO
        try:
            # Get or create DO for this key
            do = self.do.do_store.get(key)
            if not do:
                from substrate.state import DurableObjectState
                do = DurableObjectState(key)
                self.do.do_store[key] = do
            
            do.write(key, kv_state)
            
            # Log sync operation
            self.sync_log.append(
                SyncOperation(
                    id=f"sync_{time.time()}",
                    key=key,
                    source="kv",
                    target="do",
                    data=kv_state,
                    timestamp=time.time(),
                    status="complete",
                )
            )
            return True
        except Exception as e:
            print(f"[SUBSTRATE] KV→DO sync failed: {e}")
            return False
    
    def verify_coherence(self, key: str) -> bool:
        """
        Verify DO and KV states are coherent.
        Returns True if states match.
        """
        do_state = self.do.store.get(key)
        kv_state = self.kv.get(key)
        
        if not do_state and not kv_state:
            return True  # Both empty
        
        if not do_state or not kv_state:
            return False  # One empty, one not
        
        # Compare values
        return do_state.data == kv_state
    
    def repair_coherence(self, key: str) -> bool:
        """
        Repair state coherence.
        DO is source of truth, so sync to KV.
        """
        if not self.verify_coherence(key):
            return self.sync_do_to_kv(key)
        return True


class TransactionLog:
    """
    Transaction log for state changes.
    Enables recovery and replay.
    """
    
    def __init__(self):
        self.entries: List[Dict[str, Any]] = []
    
    def append(self, operation: str, key: str, value: Dict[str, Any]) -> None:
        """
        Append transaction to log.
        """
        self.entries.append({
            "timestamp": time.time(),
            "operation": operation,
            "key": key,
            "value": value,
        })
    
    def replay(self, target_store, from_index: int = 0) -> bool:
        """
        Replay transactions to recover state.
        """
        for i in range(from_index, len(self.entries)):
            entry = self.entries[i]
            
            if entry["operation"] == "write":
                target_store.put(entry["key"], entry["value"])
            elif entry["operation"] == "delete":
                # TODO: Implement delete
                pass
        
        return True
