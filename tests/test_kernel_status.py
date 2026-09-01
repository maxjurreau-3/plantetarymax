import time
from kernel.boot import KernelBoot
from substrate.helpers import get_kernel_status


def test_kernel_boot_writes_status():
    """Boot the kernel and ensure kernel status is persisted (dev/local fallback)."""
    boot = KernelBoot()
    state = boot.boot()

    # Kernel boot should reach READY phase under current invariants
    assert state.phase.value == "ready"

    # get_kernel_status should return a dict with phase and updated_at
    status = get_kernel_status()
    assert status is not None, "expected kernel status to be available after boot"
    assert isinstance(status, dict)
    assert status.get("phase") in ("ready", "ready"), f"unexpected phase: {status.get('phase')}"
    assert "updated_at" in status
