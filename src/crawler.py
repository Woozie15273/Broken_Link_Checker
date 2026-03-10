import asyncio
import logging
from src.models import ValidationResult
from playwright.async_api import async_playwright
from src.config import *

logging.basicConfig(level=logging.INFO)

def normalize_url(url: str) -> str:
    """Strip fragments and trailing slashes for consistency."""
    return url.split('#')[0].rstrip('/')

class LinkScout:
    def __init__(self, targets):
        self.targets = targets
        self.limit = asyncio.Semaphore(CONCURRENCY_LIMIT)
        self.validation_queue: list[ValidationResult] = []
        self.visited: set[str] = set()
        self.user_agent = DEFAULT_UA
        self.timeout = TIMEOUT_SECONDS * 3000

    async def run(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=self.user_agent)

            for target in self.targets:
                await self.explore(context, target['base_url'], target['levels'])

            await context.close()
            await browser.close()
            return self.validation_queue

    async def explore(self, context, url, levels):
        url = normalize_url(url)
        if not levels:
            return # Step recursion if no more lvls remain

        # Extract the current crawling lvl and the remaining lvls
        current_level, *remaining_levels = levels
        found_links = []

        async with self.limit:
            page = await context.new_page()
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=self.timeout)
                await self._trigger_js_content(page)

                elements = await page.query_selector_all(current_level['selector'])
                for el in elements:
                    href = await el.get_attribute('href')
                    if not href or href.startswith(('mailto:', 'tel:', 'javascript:')):
                        continue # Skip invalid or non-navigable links

                    # Convert relative URLs to absolute URLs
                    text = (await el.inner_text()).strip()
                    rel_url = normalize_url(await page.evaluate(
                        f'new URL("{href}", window.location.href).href'
                    ))

                    if current_level['action'] == 'follow':
                        # Recursively crawl the link if not visited before
                        if rel_url not in self.visited:
                            self.visited.add(rel_url)
                            found_links.append(rel_url)
                            
                    elif current_level['action'] == 'validate':
                        # Store the link for later validation
                        self.validation_queue.append(ValidationResult(rel_url, text, url))

            except Exception as e:
                logging.error(f"Error crawling {url}: {e}", exc_info=True)
            finally:
                await page.close()

        # Recursively explore all discovered links for the next levels
        if found_links:
            await asyncio.gather(
                *(self.explore(context, link, remaining_levels) for link in found_links),
                return_exceptions=True # Prevent one failure from stopping the whole batch
            )

    async def _trigger_js_content(self, page):
        """ Future-proof placeholder: current resources has no lazy loading function. """
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            await asyncio.sleep(1)
