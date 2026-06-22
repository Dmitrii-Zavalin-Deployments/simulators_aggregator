# tests/architecture/test_hygiene_and_archivist.py

from src.io.dropbox_utils import TokenManager
from src.core.update_ledger import LedgerManager

def test_archivist_memory_optimization():
    """
    CONSTITUTION CHECK: Phase C (5) - Rule 0 (__slots__) Compliance.
    Verifies that the TokenManager uses __slots__ to eliminate memory overhead.
    """
    tm = TokenManager(client_id="test_id", client_secret="test_secret")
    
    # RULE: Classes in src/io/ must use __slots__. __dict__ should not exist.
    assert not hasattr(tm, '__dict__'), "❌ RULE 0 VIOLATION: TokenManager is missing __slots__."
    print("✅ Rule 0 Verified: TokenManager is memory-optimized.")

def test_audit_atomic_prepending(tmp_path):
    """
    CONSTITUTION CHECK: Phase C (5) - Performance Logging.
    Verifies that new events are prepended (Newest First) to the audit log.
    """
    audit_file = tmp_path / "performance_audit.md"
    ledger = LedgerManager(log_path=str(audit_file))
    
    # 1. Record First Event
    ledger.record_event("INITIALIZE", "Engine Start")
    
    # 2. Record Second Event (Must appear at the top)
    ledger.record_event("SYNC", "Dropbox Ingestion Complete")
    
    with open(audit_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
        # Find the indices of the entries (skipping the header)
        sync_index = next(i for i, line in enumerate(lines) if "SYNC" in line)
        init_index = next(i for i, line in enumerate(lines) if "INITIALIZE" in line)
        
        # RULE: Newer events must have a lower index (appear earlier in file)
        assert sync_index < init_index, "❌ HYGIENE VIOLATION: Audit log is not prepending newest events first."
        
    print("✅ Operational Hygiene Verified: Audit log follows Atomic Prepending rule.")

def test_ingestion_binary_integrity():
    """
    CONSTITUTION CHECK: Phase C (5) - Clean Room Sync.
    Verifies that CloudIngestor uses binary mode for artifact safety.
    """
    # Forensic check of the source code for binary write 'wb'
    from src.io.download_from_dropbox import CloudIngestor
    import inspect
    
    source = inspect.getsource(CloudIngestor._download_file)
    assert 'open(local_path, "wb")' in source, "❌ RULE 1 VIOLATION: Ingestor must use binary mode for artifact integrity."
    print("✅ Clean Room Sync Verified: Artifacts are written in binary mode.")