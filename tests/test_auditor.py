import pytest
from src.auditor import Auditor

@pytest.mark.asyncio
async def test_auditor(mock_results):
    audit = Auditor()
    results = await audit.audit_all(mock_results)
    assert isinstance(results, list)
    assert all(hasattr(r, "status_code") for r in results)
