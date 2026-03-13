import csv
from dataclasses import asdict
from datetime import datetime
import logging
from typing import List
from pathlib import Path

from src.auditor import Auditor
from src.crawler import LinkScout
from src.models import AuditResult, ValidationResult
from src.config import BASE_DIR

logging.basicConfig(level=logging.INFO)

class Manager:

    def __init__(self):        
        self.report_path: Path = self._prepare_workspace()
        self.scout = LinkScout()
        self.auditor = Auditor()

    def _prepare_workspace(self) -> Path:
        report_dir = BASE_DIR / "data" / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        return report_dir / f"audit_{timestamp}.csv"

    def generate_report(self, results: List[AuditResult]):
        if not results:
            logging.error("Director: No results found to report.")
            return None
        
        # Sort: broken links first, then group by parent page
        results.sort(key = lambda x: (not x.is_broken, x.parent))

        # Extract headers from the first dataclass obj
        headers = asdict(results[0]).keys()

        try:
            with open(self.report_path, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()

                for res in results:
                    writer.writerow(asdict(res))
            
            logging.info(f"Director: Report generated at {self.report_path}")

        except IOError as e:
            logging.error(f"Director: Failed to write report. {e}")
            return None
    
    async def run(self, targets):
        logging.info(f"Manager: Staring the full lifecycle:")
        to_validate : list[ValidationResult] = await self.scout.run(targets)
        logging.info(f"Move on to audition phase.")
        to_export: list[AuditResult] = await self.auditor.audit_all(to_validate)
        logging.info(f"Start report generation.")
        self.generate_report(to_export)




