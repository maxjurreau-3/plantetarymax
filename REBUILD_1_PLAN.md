# Rebuild 1 — Proof of Concept

**Status:** Documented Baseline  
**Purpose:** Establish the minimal end-to-end loop that proves Portal-OS architecture works

---

## 🎯 Core Vision

**Goal:** Create a minimal, end‑to‑end proof‑of‑concept OS that:

- Accepts a request at the Worker surface
- Routes it into a Kernel
- Runs through a tiny cognitive/execution path
- Returns a response

**Constraint:** No performance, no persistence, no governance—just **"can this architecture even run?"**

---

## 🧱 Core Capabilities (Minimal)

Rebuild 1 does only this:

1. **Handle a basic request** (HTTP or direct call)
2. **Route it into a Kernel**
3. **Run a trivial cognitive step** (e.g., echo, simple rule)
4. **Run a trivial execution step** (e.g., log, transform)
5. **Return a response**

---

## 📁 Architecture

### Layer 1: Worker Surface
**File:** `rebuild_1/worker/bridge.py`

**Responsibility:**
- Accept a request (string, JSON, dict)
- Call `kernel.handle(request)`
- Return the result

```python
def handle_request(request):
    """Entry point for all requests."""
    return kernel.handle(request)
```

---

### Layer 2: Kernel Core
**File:** `rebuild_1/kernel/core.py`

**Responsibility:**
- Basic boot function
- Minimal set of invariants (e.g., "request must be non-empty")
- Dispatch to cognitive + execution stubs

```python
class Kernel:
    def __init__(self):
        self.scheduler = None
        self.sim = None
        self.tec = None
        self.invariants = {}
    
    def boot(self):
        """Initialize kernel components."""
        self._validate_invariants()
        self.scheduler = Scheduler()
        self.sim = SIMCore()
        self.tec = TECCore()
    
    def handle(self, request):
        """Process a single request through the loop."""
        # Validate invariant
        if not request or (isinstance(request, dict) and not request):
            raise ValueError("Request cannot be empty")
        
        # Run through cognitive lane
        cognitive_result = self.scheduler.process(request)
        
        # Run through execution layer
        response = self.tec.execute(cognitive_result)
        
        return response
```

---

### Layer 3: Scheduler (Single Lane)
**File:** `rebuild_1/kernel/scheduler.py`

**Responsibility:**
- Single lane only: `COGNITIVE`
- Synchronous processing
- Calls `sim.process(request)` directly

```python
class Scheduler:
    def __init__(self):
        self.lanes = {
            'cognitive': []
        }
    
    def process(self, request):
        """Process request through cognitive lane."""
        # No queuing, no async—just direct call
        return sim.process(request)
```

---

### Layer 4: SIM Skeleton
**File:** `rebuild_1/sim/core.py`

**Responsibility:**
- Take input
- Apply a trivial rule (e.g., "if field X exists, add field Y")
- Return a "thought" or intermediate result

```python
class SIMCore:
    def __init__(self):
        self.state = {}
        self.trajectory = []
    
    def process(self, request):
        """Apply a simple cognitive rule."""
        # Trivial rule: echo request + add metadata
        result = {
            'input': request,
            'metadata': {
                'processed': True,
                'timestamp': time.time()
            }
        }
        
        self.trajectory.append(result)
        return result
```

---

### Layer 5: TEC Skeleton
**File:** `rebuild_1/tec/core.py`

**Responsibility:**
- Take SIM output
- Perform a simple action (e.g., wrap in response object)
- Return final result

```python
class TECCore:
    def __init__(self):
        self.log = []
    
    def execute(self, cognitive_result):
        """Execute SIM result into a response."""
        response = {
            'status': 'success',
            'data': cognitive_result,
            'execution_id': str(uuid.uuid4())
        }
        
        self.log.append(response)
        return response
```

---

### Layer 6: Routing Stub
**File:** `rebuild_1/routing/router.py`

**Responsibility:**
- Hardcode the loop: Worker → Kernel → SIM → TEC → Response
- No dynamic routing, no identity, no governance

```python
class Router:
    """Hardcoded routing for Rebuild 1."""
    
    ROUTE = ['WORKER', 'KERNEL', 'SIM', 'TEC', 'RESPONSE']
    
    @staticmethod
    def trace(request):
        """Log the request path through the system."""
        print(f"Request path: {' -> '.join(Router.ROUTE)}")
```

---

### Layer 7: Substrate Stub
**File:** `rebuild_1/substrate/state.py`

**Responsibility:**
- In-memory dict only
- Store last request/response
- No durability, no DO/KV

```python
class SubstrateState:
    """In-memory state store for Rebuild 1."""
    
    def __init__(self):
        self.store = {}
    
    def set(self, key, value):
        """Store a value."""
        self.store[key] = value
    
    def get(self, key):
        """Retrieve a value."""
        return self.store.get(key)
    
    def save_request(self, request):
        """Record incoming request."""
        self.set('last_request', request)
    
    def save_response(self, response):
        """Record outgoing response."""
        self.set('last_response', response)
```

---

## ✅ Invariants (Minimal Set)

Rebuild 1 maintains these baseline invariants:

1. **Request Non-Empty** — Every request must be non-empty
2. **Kernel Boots** — Kernel must boot successfully before processing
3. **Loop Completes** — Request must flow through all layers and return
4. **Response Valid** — Every response must have `status` and `data` fields

---

## 🧪 Tests

**File:** `rebuild_1/tests/test_rebuild_1.py`

```python
def test_basic_loop():
    """Given input X, system returns Y."""
    kernel = Kernel()
    kernel.boot()
    
    request = {'message': 'hello'}
    response = kernel.handle(request)
    
    assert response['status'] == 'success'
    assert response['data']['input'] == request
    assert 'execution_id' in response

def test_invariant_non_empty_request():
    """Empty requests are rejected."""
    kernel = Kernel()
    kernel.boot()
    
    with pytest.raises(ValueError):
        kernel.handle({})

def test_end_to_end():
    """Full loop: Worker → Kernel → SIM → TEC → Response."""
    from rebuild_1.worker.bridge import handle_request
    
    request = {'test': 'data'}
    response = handle_request(request)
    
    assert 'status' in response
    assert response['status'] == 'success'
```

---

## 📊 Success Criteria

Rebuild 1 is complete when:

- ✅ You can run a single Python command:
  ```bash
  python -c "from rebuild_1.worker.bridge import handle_request; print(handle_request({'message': 'hello'}))"
  ```
  
- ✅ Output shows:
  - Request received
  - Kernel processed it
  - SIM transformed it
  - TEC wrapped it
  - Response returned with all layers intact

- ✅ All invariants hold (no crashes under simple use)

- ✅ Architecture feels coherent enough to justify Rebuild 2

---

## 🚀 Why Rebuild 2?

After Rebuild 1 works:

- **Add real persistence** (Substrate state model)
- **Add multi-lane scheduling** (Cognitive, Orchestration, Governance, Substrate)
- **Add governance + identity** (Authorization, identity enforcement)
- **Add routing intelligence** (Dynamic routing based on metadata)
- **Add error handling** (Escalation, retry logic)

---

## 📝 Limitations (Intentional)

Rebuild 1 does **not** have:

- ❌ Persistence (everything in-memory)
- ❌ Governance (no authorization checks)
- ❌ Identity (no user/agent tracking)
- ❌ Performance (no optimization)
- ❌ Concurrency (single-threaded)
- ❌ Distributed state (no DO/KV)
- ❌ Error recovery (basic validation only)

These are **by design** — Rebuild 1 is about proof-of-concept, not production.

---

**Created:** 2026-08-27  
**Rebuild:** 1  
**Status:** Baseline Architecture Documented
