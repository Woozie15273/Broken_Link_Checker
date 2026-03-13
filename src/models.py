from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class ValidationResult:
    """The raw data captured by the Scout (crawler.py)."""
    url: str
    text: str
    parent: str

@dataclass
class AuditResult:
    url: str
    text: str
    parent: str
    status_code: int
    final_url: str
    latency: float
    failure_type: Optional[str] = None
    is_broken: bool = False

    def __post_init__(self):
        if self.failure_type or self.status_code >= 400 or self.status_code == 0:
            self.is_broken = True