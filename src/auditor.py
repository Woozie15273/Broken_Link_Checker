import asyncio
import logging
import httpx
import time
from typing import List
from src.models import ValidationResult, AuditResult
from src.config import *
import re

logging.basicConfig(level=logging.INFO)

class Auditor:
    def __init__(self):
        self.semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
        self.timeout = httpx.Timeout(TIMEOUT_SECONDS, connect=5.0)
        self.headers = DEFAULT_HEADER
        self._fallback_codes = FALLBACK_CODES
        self._soft404_keywords = SOFT_404_KEYWORDS
        self._error_paths = ERROR_PATHS

    # ---------------------------------------------------------
    # Enhanced Soft‑404 Detection
    # ---------------------------------------------------------
    def _rule_path_fallback(self, url: str, response: httpx.Response) -> bool:
        """
        Detect when a missing page is redirected to a completely different path.
        Should NOT trigger on:
        - http → https upgrade
        - trailing slash differences
        - trivial normalization
        """
        orig_url = httpx.URL(url)
        final_url = response.url

        # 1. Ignore scheme changes (http → https)
        if orig_url.host == final_url.host and orig_url.path == final_url.path:
            return False

        # 2. Normalize trailing slashes
        orig_path = orig_url.path.rstrip("/")
        final_path = final_url.path.rstrip("/")

        # If paths are identical after normalization → not soft 404
        if orig_path == final_path:
            return False
        
        # 3. Detect real fallback: original path is non-empty but final path becomes empty
        #    Example: /abc → /
        return bool(orig_path and not final_path)

    def _rule_small_content(self, text: str) -> bool:
        # Ignore whitespace-only content
        cleaned = text.strip()

        # Very small HTML skeleton should not count as soft 404
        if cleaned.lower() in ("<html></html>", "<html><body></body></html>"):
            return False

        return len(cleaned) < 80

    def _rule_keyword_match(self, text: str) -> bool:
        lowered = text.lower()

        # Avoid matching keywords inside scripts or JSON
        # e.g. {"error":"not found"} in API responses
        visible_text = re.sub(r"<script.*?</script>", "", lowered, flags=re.DOTALL)
        visible_text = re.sub(r"{.*?}", "", visible_text, flags=re.DOTALL)
        
        return any(k in visible_text for k in self._soft404_keywords)

    def _rule_title_match(self, text: str) -> bool:
        m = re.search(r"<title[^>]*>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
        if not m:
            return False
        title = m.group(1).strip().lower()

        # Avoid false positives like "404 ways to cook eggs"
        if re.search(r"\b404\b", title) or "not found" in title:
            return True

        return False


    def _rule_error_path(self, response: httpx.Response) -> bool:
        final_path = response.url.path.strip("/").lower()

        # Normalize trailing slash
        final_path = final_path.rstrip("/")

        return final_path in self._error_paths

    def _is_soft_404(self, url: str, response: httpx.Response) -> bool:
        text = response.text or ""

        rules = [
            self._rule_path_fallback(url, response),
            self._rule_small_content(text),
            self._rule_keyword_match(text),
            self._rule_title_match(text),
            self._rule_error_path(response),
        ]

        # Soft 404 only if 2 or more rules hit
        return sum(bool(r) for r in rules) >= 2

    # ---------------------------------------------------------
    # URL Probe
    # ---------------------------------------------------------
    def _is_file_response(self, response: httpx.Response) -> bool:
        content_type = response.headers.get("Content-Type", "").lower()
        content_disp = response.headers.get("Content-Disposition", "").lower()

        return (
            "attachment" in content_disp
            or content_type.startswith("application/")
            or content_type.startswith("image/")
            or content_type.startswith("audio/")
            or content_type.startswith("video/")
            or content_type == "application/octet-stream"
        )
    
    async def _probe_url(self, client: httpx.AsyncClient, result: ValidationResult) -> AuditResult:
        async with self.semaphore:
            await asyncio.sleep(1) # Small delay to reduce burst load on target domains

            start = time.perf_counter()
            url = result.url.strip()

            try:
                # Starting from a GET instead of HEAD as the later is not supported by many sites
                response = await client.get(url, follow_redirects=True)

                latency = round(time.perf_counter() - start, 3)

                # Skip soft‑404 detection for file-like responses
                if self._is_file_response(response):
                    return AuditResult(
                        url=url,
                        text=result.text,
                        parent=result.parent,
                        status_code=response.status_code,
                        final_url=str(response.url),
                        latency=latency,
                        failure_type=None
                    )

                # Soft‑404 detection only applies to successful (200 OK) responses.
                is_soft_404 = False
                if response.status_code == 200:
                    is_soft_404 = self._is_soft_404(url, response)

                logging.info(f"Auditor: Completed audition on {url}")

                # Build a successful audit result, including final URL after redirects
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
            status_code=0, # - status_code is set to 0 because no valid HTTP status exists.
            final_url=res.url, # - final_url remains the original URL since no redirect occurred.
            latency=0.0, # - latency is 0.0 because the request never completed successfully.
            failure_type=msg # - failure_type stores the specific error message for reporting.
        )

    # ---------------------------------------------------------
    # Main Audit Orchestrator
    # ---------------------------------------------------------
    async def audit_all(self, scout_results: List[ValidationResult]) -> List[AuditResult]:
        # Remove duplicate URLs while preserving the latest ValidationResult for each
        unique = {res.url: res for res in scout_results}

        limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)

        async with httpx.AsyncClient(
            http2=True,
            timeout=self.timeout,
            limits=limits,
            verify=False,
            headers=self.headers
        ) as client:

            # Launch all URL probes concurrently
            async with asyncio.TaskGroup() as tg:
                tasks = {
                    url: tg.create_task(self._probe_url(client, res))
                    for url, res in unique.items()
                }

        # Collect completed results mapped by URL
        verdicts = {url: task.result() for url, task in tasks.items()}

        # Reconstruct results in the same order as the original input list
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
