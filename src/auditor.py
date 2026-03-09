import asyncio
import httpx
import time
from typing import List, Dict
from src.models import ValidationResult, AuditResult
from src.config import *
import re

class Auditor:
    def __init__(self):
        self.semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
        self.timeout = httpx.Timeout(TIMEOUT_SECONDS, connect=5.0)
        self.headers = DEFAULT_HEADER
        self._fallback_codes = {403, 405, 501}

        # Soft‑404 keyword list (can be expanded)
        self._soft404_keywords = [
            "not found", "page not found", "404",
            "doesn't exist", "unavailable", "gone",
            "missing", "error"
        ]

        # Known error paths
        self._error_paths = {"404", "notfound", "error", "missing"}

    # ---------------------------------------------------------
    # Enhanced Soft‑404 Detection
    # ---------------------------------------------------------
    def _rule_path_fallback(self, url: str, response: httpx.Response) -> bool:
        orig = httpx.URL(url).path.strip('/')
        final = response.url.path.strip('/')
        return bool(orig and not final)

    def _rule_small_content(self, text: str) -> bool:
        return len(text) < 80

    def _rule_keyword_match(self, text: str) -> bool:
        lowered = text.lower()
        return any(k in lowered for k in self._soft404_keywords)

    def _rule_title_match(self, text: str) -> bool:
        m = re.search(r"<title>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
        if not m:
            return False
        title = m.group(1).lower()
        return "404" in title or "not found" in title

    def _rule_error_path(self, response: httpx.Response) -> bool:
        final_path = response.url.path.strip('/')
        return final_path in self._error_paths

    def _is_soft_404(self, url: str, response: httpx.Response) -> bool:
        text = response.text or ""

        return (
            self._rule_path_fallback(url, response)
            or self._rule_small_content(text)
            or self._rule_keyword_match(text)
            or self._rule_title_match(text)
            or self._rule_error_path(response)
        )

    # ---------------------------------------------------------
    # URL Probe
    # ---------------------------------------------------------
    async def _probe_url(self, client: httpx.AsyncClient, result: ValidationResult) -> AuditResult:
        async with self.semaphore:
            await asyncio.sleep(1)

            start = time.perf_counter()
            url = result.url.strip()

            try:
                # GET-only request
                response = await client.get(url, follow_redirects=True)

                latency = round(time.perf_counter() - start, 3)

                # Enhanced Soft‑404 detection
                is_soft_404 = False
                if response.status_code == 200:
                    is_soft_404 = self._is_soft_404(url, response)

                return AuditResult(
                    url=url,
                    text=result.text,
                    parent=result.parent,
                    status_code=response.status_code,
                    final_url=str(response.url),
                    latency=latency,
                    failure_type="Soft 404" if is_soft_404 else None
                )

            except (httpx.ConnectTimeout, httpx.ReadTimeout):
                return self._create_error(result, "Timeout")
            except httpx.ConnectError:
                return self._create_error(result, "Connection/DNS Error")
            except Exception as e:
                return self._create_error(result, f"Exception: {type(e).__name__}")

    # ---------------------------------------------------------
    # Error Factory
    # ---------------------------------------------------------
    def _create_error(self, res: ValidationResult, msg: str) -> AuditResult:
        return AuditResult(
            url=res.url,
            text=res.text,
            parent=res.parent,
            status_code=0,
            final_url=res.url,
            latency=0.0,
            failure_type=msg
        )

    # ---------------------------------------------------------
    # Main Audit Orchestrator
    # ---------------------------------------------------------
    async def audit_all(self, scout_results: List[ValidationResult]) -> List[AuditResult]:
        # Deduplicate URLs
        unique = {res.url: res for res in scout_results}

        limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)

        async with httpx.AsyncClient(
            http2=True,
            timeout=self.timeout,
            limits=limits,
            verify=False,
            headers=self.headers
        ) as client:

            # Run tasks concurrently
            async with asyncio.TaskGroup() as tg:
                tasks = {
                    url: tg.create_task(self._probe_url(client, res))
                    for url, res in unique.items()
                }

        # Map results
        verdicts = {url: task.result() for url, task in tasks.items()}

        # Expand back to original list
        return [
            AuditResult(
                url=orig.url,
                text=orig.text,
                parent=orig.parent,
                status_code=verdicts[orig.url].status_code,
                final_url=verdicts[orig.url].final_url,
                latency=verdicts[orig.url].latency,
                failure_type=verdicts[orig.url].failure_type,
                is_broken=verdicts[orig.url].is_broken
            )
            for orig in scout_results
        ]
