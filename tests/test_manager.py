import pytest
from src.auditor import Auditor
from src.manager import Manager
from src.crawler import LinkScout
from src.models import AuditResult, ValidationResult

class TestManager:
    def setup_method(self):
        self.scout = LinkScout()
        self.audit = Auditor()
        self.manager = Manager()        

    @pytest.mark.asyncio
    async def test_manager_mock(self, mock_results):
        results = await self.audit.audit_all(mock_results)
        self.manager.generate_report(results)
        assert self.manager.report_path.stat().st_size > 0
    
    @pytest.mark.asyncio
    async def test_manager_real(self, targets):
        to_validate : list[ValidationResult] = await self.scout.run(targets)
        to_export: list[AuditResult] = await self.audit.audit_all(to_validate)
        self.manager.generate_report(to_export)
        assert self.manager.report_path.stat().st_size > 0